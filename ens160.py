"""
ENS160 + AHT21 combo board quick-test
• Reads T / RH from the AHT21
• Injects those values into the ENS160 for compensation
• Prints eCO2 (ppm), TVOC (ppb) and IAQ index every second
"""

import time
import board
import busio
import adafruit_ens160
import adafruit_ahtx0

# ---------------------------------------------------------------------
# I²C setup
# ---------------------------------------------------------------------
i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)

# ENS160 default address 0x53 (0x52 if the ADDR pad is tied low)
ens = adafruit_ens160.ENS160(i2c)
ens.operation_mode = adafruit_ens160.MODE_STANDARD   # or .MODE_IDLE / .MODE_SLEEP

# AHT21 address 0x38
aht = adafruit_ahtx0.AHTx0(i2c)

print("Press Ctrl-C to stop\n")
# ---------------------------------------------------------------------
while True:
    # 1. Measure ambient T / RH with the AHT21
    t_c  = aht.temperature
    rh   = aht.relative_humidity

    # 2. Give these values to the ENS160 for automatic compensation
    ens.temperature = t_c
    ens.humidity    = rh

    # 3. Read ENS160 outputs
    print(
        f"AQI  : {ens.AQI:2d}  (1=good … 5=unhealthy)   "
        f"eCO₂ : {ens.eCO2:4d} ppm   "
        f"TVOC : {ens.TVOC:4d} ppb   "
        f"[{t_c:5.2f} °C  {rh:5.1f} %RH]"
    )

    time.sleep(1)
