from gpiozero import LED

# BCM GPIO numbers
_GREEN  = LED(8)
_BLUE   = LED(11)
_RED    = LED(25)
_YELLOW = LED(9)

def set_leds(R=0, G=0, Y=0, B=0):
    _RED.value    = 1 if R else 0
    _GREEN.value  = 1 if G else 0
    _YELLOW.value = 1 if Y else 0
    _BLUE.value   = 1 if B else 0

def parse_bits(s: str):
    """
    Accepts input like:
      - "1 0 1 0"
      - "1010"
      - "R=1 G=0 Y=1 B=0"
    Returns (R,G,Y,B) as ints 0/1.
    """
    s = s.strip().upper().replace(",", " ")
    if not s:
        raise ValueError("empty input")

    # Case 1: "1010"
    if len(s.replace(" ", "")) == 4 and all(c in "01" for c in s.replace(" ", "")):
        bits = s.replace(" ", "")
        return tuple(int(c) for c in bits)  # R,G,Y,B

    # Case 2: "1 0 1 0"
    parts = s.split()
    if len(parts) == 4 and all(p in ("0", "1") for p in parts):
        return tuple(int(p) for p in parts)

    # Case 3: "R=1 G=0 Y=1 B=0"
    vals = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k in ("R", "G", "Y", "B") and v in ("0", "1"):
                vals[k] = int(v)
    if all(k in vals for k in ("R", "G", "Y", "B")):
        return vals["R"], vals["G"], vals["Y"], vals["B"]

    raise ValueError('Use "1010" or "1 0 1 0" or "R=1 G=0 Y=1 B=0" (order is R G Y B).')

if __name__ == "__main__":
    try:
        while True:
            user = input("Set LEDs as R G Y B (e.g., 1010) or 'q' to quit: ").strip()
            if user.lower() in ("q", "quit", "exit"):
                break

            try:
                R, G, Y, B = parse_bits(user)
                set_leds(R=R, G=G, Y=Y, B=B)
                print(f"Set: R={R} G={G} Y={Y} B={B}")
            except ValueError as e:
                print("Invalid input:", e)

    finally:
        # turn off + release GPIO resources
        for led in (_RED, _GREEN, _YELLOW, _BLUE):
            led.off()
            led.close()
