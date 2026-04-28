"""
sht31_test.py – quick sanity-check for a Sensirion SHT31-D
  • Works on Raspberry Pi / any Linux SBC with I²C.
  • Uses single-shot high-repeatability measurement (0x2400).
  • Performs CRC-8 check on both T and RH words.
"""

import time
from smbus2 import SMBus

I2C_BUS   = 1          # 1 on newer RPis; adjust if you use a different bus
SHT31_ADDR = 0x44      # ADDR pulled low → 0x44, high → 0x45

# Command bytes (see datasheet, table 10)
CMD_SINGLE_SHOT_HIGHREP = (0x24, 0x00)

# ---------------------------------------------------------------------------
def _crc8(data: bytes) -> int:
    """Calculate Sensirion CRC-8 over 2 data bytes."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc << 1) ^ 0x31 if (crc & 0x80) else (crc << 1)
            crc &= 0xFF
    return crc
# ---------------------------------------------------------------------------


def read_sht31_once(bus: SMBus, addr: int = SHT31_ADDR):
    """Trigger one measurement and return (temperature_C, rel_humidity_%)."""
    # 1. Send command
    bus.write_i2c_block_data(addr, CMD_SINGLE_SHOT_HIGHREP[0],
                             [CMD_SINGLE_SHOT_HIGHREP[1]])

    # 2. Wait t_meas,max = 15 ms (datasheet), add a small cushion
    time.sleep(0.020)

    # 3. Read 6 bytes: T_MSB, T_LSB, T_CRC, RH_MSB, RH_LSB, RH_CRC
    raw = bus.read_i2c_block_data(addr, 0x00, 6)
    t_raw = bytes(raw[0:2]); t_crc = raw[2]
    rh_raw = bytes(raw[3:5]); rh_crc = raw[5]

    if _crc8(t_raw) != t_crc or _crc8(rh_raw) != rh_crc:
        raise RuntimeError("CRC mismatch – check wiring and pull-ups")

    # Convert to physical units (datasheet, section 4.12)
    t_ticks = int.from_bytes(t_raw, "big")
    rh_ticks = int.from_bytes(rh_raw, "big")

    temperature = -45 + 175 * (t_ticks / 65535)
    humidity    = 100 * (rh_ticks / 65535)

    return temperature, humidity


def main():
    with SMBus(I2C_BUS) as bus:
        try:
            print("Press Ctrl-C to stop\n")
            while True:
                t, h = read_sht31_once(bus)
                print(f"{t:6.2f} °C   {h:6.2f} %RH")
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
