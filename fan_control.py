#!/usr/bin/env python3
# interactive_fan_lgpio_compat.py
# -------------------------------------------------------------------
# One-file, *daemon-free* fan controller that works with **any** known
# lgpio build – even the very old ones that lack tx_pwm().
#
# Priority of PWM implementations
#   1. tx_pwm() / gpio_tx_pwm()      ‒ kernel-side, low-CPU    (≈≤3 kHz)
#   2. wave_tx_repeat()              ‒ DMA waveform, low-CPU   (≈≤10 kHz)
#   3. thread-based bit-bang         ‒ pure Python, >CPU       (≈≤1 kHz)
#
# Type a duty-cycle 0-100 in the prompt; q / Ctrl-C exits cleanly.
# -------------------------------------------------------------------
from __future__ import annotations

import sys
import threading
import time
from typing import Callable, Optional, Tuple

try:
    import lgpio  # type: ignore
except ModuleNotFoundError:
    sys.exit("ERROR:  python3 -m pip install lgpio   (module not found)")

# ─────────────────────── user tweaks ────────────────────────────────
PWM_PIN      = 12        # BCM number (physical pin 32)
FREQ_DESIRED = 2_000     # Hz  (used when kernel PWM is available)
FREQ_THREAD  = 400       # Hz  (used by software bit-bang fallback)
INVERT       = True      # True if an NPN pulls the PWM line LOW
# ─────────────────────────────────────────────────────────────────────

# open gpiochip
try:
    h = lgpio.gpiochip_open(0)
except Exception as e:
    sys.exit(f"ERROR: cannot open /dev/gpiochip0 – {e}")

# claim the GPIO as output (handle both old & new APIs)
claimed = False
for fn_name in ("set_mode", "gpio_claim_output", "gpioClaimOutput"):
    if hasattr(lgpio, fn_name):
        fn: Callable = getattr(lgpio, fn_name)  # type: ignore
        try:
            if fn_name == "set_mode":
                fn(h, PWM_PIN, lgpio.MODE_OUTPUT)       # new API
            else:
                fn(h, PWM_PIN, 0)                       # old API
            claimed = True
            break
        except Exception:
            pass
if not claimed:
    lgpio.gpiochip_close(h)
    sys.exit(f"ERROR: could not set BCM {PWM_PIN} as output with this lgpio build.")

# helper to invert duty if needed
def _effective_pct(p: float) -> float:
    p = max(0.0, min(100.0, p))
    return 100.0 - p if INVERT else p

driver_name: str

# ───────────────── 1. kernel-PWM via tx_pwm()  ──────────────────────
_tx: Optional[Callable[[int, int], None]] = None
period_us = int(round(1_000_000 / FREQ_DESIRED))

if hasattr(lgpio, "tx_pwm"):
    print("tx_pwm")
    def _tx(percent: float) -> None:
        lgpio.tx_pwm(h, PWM_PIN, FREQ_DESIRED, percent, 0, 0)
    driver_name = f"tx_pwm() @ {FREQ_DESIRED/1_000:g} kHz"
    
elif hasattr(lgpio, "gpio_tx_pwm"):
    print("gpio_tx_pwm")
    def _tx(percent: float) -> None:
        lgpio.gpio_tx_pwm(h, PWM_PIN, FREQ_DESIRED, percent, 0, 0)
    driver_name = f"gpio_tx_pwm() @ {FREQ_DESIRED/1_000:g} kHz"
    
# ───────────────── 2. DMA waveform fallback  ────────────────────────
elif hasattr(lgpio, "wave_tx_repeat"):
    print("wave_tx_repeat")

    def _build_wave(high: int, low: int) -> int:
        lgpio.wave_add_generic(
            h,
            [lgpio.pulse(1 << PWM_PIN, 0, high),
             lgpio.pulse(0, 1 << PWM_PIN, low)],
        )
        return lgpio.wave_create(h)

    _last_wave: Optional[int] = None

    def _tx(high_us: int, low_us: int) -> None:  # type: ignore
        global _last_wave
        wid = _build_wave(high_us, low_us)
        lgpio.wave_send_repeat(h, wid)
        if _last_wave is not None:
            lgpio.wave_delete(h, _last_wave)
        _last_wave = wid

    driver_name = "wave_tx_repeat() @ ≈DMA"

    # keep DMA engine clean at start
    lgpio.wave_clear(h)

# ───────────────── 3. Threaded bit-bang software PWM  ───────────────
else:
    print("else branch fallback")
    _duty_pct = 0.0
    _exit = threading.Event()

    def _worker() -> None:
        period = 1.0 / FREQ_THREAD
        while not _exit.is_set():
            on = period * (_duty_pct / 100.0)
            off = period - on
            lgpio.gpio_write(h, PWM_PIN, 0 if INVERT else 1)
            time.sleep(on)
            lgpio.gpio_write(h, PWM_PIN, 1 if INVERT else 0)
            time.sleep(off)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    def _tx(high_us: int, low_us: int) -> None:          # type: ignore
        # store duty for the worker thread (µs ⇒ %)
        global _duty_pct
        _duty_pct = high_us * 100.0 / (high_us + low_us)

    period_us = int(round(1_000_000 / FREQ_THREAD))
    driver_name = f"thread-PWM @ {FREQ_THREAD} Hz (CPU load)"

print(f"[INFO] lgpio driver active – {driver_name}")

# common set_duty implementation for whichever driver we picked
def set_duty(percent: float) -> None:
    pct = _effective_pct(percent)
    high = int(round(period_us * pct / 100.0))
    low = period_us - high
    _tx(high, low)  # type: ignore

if (hasattr(lgpio, "tx_pwm")) or (hasattr(lgpio, "gpio_tx_pwn")):
    def set_duty(percent: float) -> None:
        pct = _effective_pct(percent)
        _tx(pct)


# graceful cleanup
def cleanup() -> None:
    try:
        set_duty(0)
        if hasattr(lgpio, "wave_tx_stop"):
            lgpio.wave_tx_stop(h)
    finally:
        if '_exit' in globals():
            _exit.set()
        lgpio.gpiochip_close(h)


# ───────────────────── interactive shell loop ───────────────────────
print("\nType a number 0-100 to set duty, or 'q' to quit.")

try:
    while True:
        try:
            cmd = input("fan%> ").strip()
        except EOFError:
            break
        if cmd.lower().startswith("q"):
            break
        try:
            pct = float(cmd)
        except ValueError:
            print("  ↳ enter a number 0-100 or q")
            continue
        set_duty(pct)
        print(f"  ↳ duty set to {pct:.1f} %")
except KeyboardInterrupt:
    pass
finally:
    cleanup()
    print("\nFan stopped, GPIO released. Bye!")


