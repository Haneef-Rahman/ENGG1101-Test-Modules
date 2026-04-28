import time
import lgpio

h = lgpio.i2c_open(1, 0x48)

def read_ch(ch):
    msb = [0xC3, 0xD3, 0xE3, 0xF3][ch]  # OS=1, single-ended A0/A1/A2/A3, PGA=4.096V, MODE=single-shot
    lgpio.i2c_write_device(h, [0x01, msb, 0x83])  # Config register
    time.sleep(0.02)  # give conversion time
    lgpio.i2c_write_device(h, [0x00])  # Conversion register
    _, d = lgpio.i2c_read_device(h, 2)
    raw = (d[0] << 8) | d[1]
    if raw & 0x8000:
        raw -= 0x10000
    return raw

try:
    while True:
        print("MQ2:", read_ch(0), "MQ7:", read_ch(1))
        time.sleep(1)
finally:
    lgpio.i2c_close(h)
