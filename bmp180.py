import time
from smbus2 import SMBus

# BMP180 default address
BMP180_ADDR = 0x77

# Registers
REG_CALIB = 0xAA
REG_CONTROL = 0xF4
REG_RESULT = 0xF6

CMD_READ_TEMP = 0x2E
CMD_READ_PRESSURE = 0x34

# Oversampling setting (0..3). We'll use 0 for simplicity.
OSS = 0

class BMP180:
    def __init__(self, bus_num=1):
        self.bus = SMBus(bus_num)
        self._read_calibration_data()

    def _read_signed_16bit(self, reg):
        msb = self.bus.read_byte_data(BMP180_ADDR, reg)
        lsb = self.bus.read_byte_data(BMP180_ADDR, reg + 1)
        value = (msb << 8) + lsb
        if value > 32767:
            value -= 65536
        return value

    def _read_unsigned_16bit(self, reg):
        msb = self.bus.read_byte_data(BMP180_ADDR, reg)
        lsb = self.bus.read_byte_data(BMP180_ADDR, reg + 1)
        return (msb << 8) + lsb

    def _read_calibration_data(self):
        self.AC1 = self._read_signed_16bit(0xAA)
        self.AC2 = self._read_signed_16bit(0xAC)
        self.AC3 = self._read_signed_16bit(0xAE)
        self.AC4 = self._read_unsigned_16bit(0xB0)
        self.AC5 = self._read_unsigned_16bit(0xB2)
        self.AC6 = self._read_unsigned_16bit(0xB4)
        self.B1  = self._read_signed_16bit(0xB6)
        self.B2  = self._read_signed_16bit(0xB8)
        self.MB  = self._read_signed_16bit(0xBA)
        self.MC  = self._read_signed_16bit(0xBC)
        self.MD  = self._read_signed_16bit(0xBE)

    def _read_raw_temp(self):
        self.bus.write_byte_data(BMP180_ADDR, REG_CONTROL, CMD_READ_TEMP)
        time.sleep(0.005)  # 4.5ms
        msb = self.bus.read_byte_data(BMP180_ADDR, REG_RESULT)
        lsb = self.bus.read_byte_data(BMP180_ADDR, REG_RESULT + 1)
        return (msb << 8) + lsb

    def _read_raw_pressure(self):
        self.bus.write_byte_data(
            BMP180_ADDR,
            REG_CONTROL,
            CMD_READ_PRESSURE + (OSS << 6)
        )
        time.sleep(0.005)  # enough for OSS=0
        msb = self.bus.read_byte_data(BMP180_ADDR, REG_RESULT)
        lsb = self.bus.read_byte_data(BMP180_ADDR, REG_RESULT + 1)
        xlsb = self.bus.read_byte_data(BMP180_ADDR, REG_RESULT + 2)
        up = ((msb << 16) + (lsb << 8) + xlsb) >> (8 - OSS)
        return up

    def read_temperature_pressure(self):
        UT = self._read_raw_temp()
        UP = self._read_raw_pressure()

        # Temperature calculations (datasheet)
        X1 = ((UT - self.AC6) * self.AC5) / 32768.0
        X2 = (self.MC * 2048.0) / (X1 + self.MD)
        B5 = X1 + X2
        temp_C = (B5 + 8.0) / 16.0 / 10.0  # in °C

        # Pressure calculations (datasheet)
        B6 = B5 - 4000.0
        X1 = (self.B2 * (B6 * B6 / 4096.0)) / 2048.0
        X2 = (self.AC2 * B6) / 2048.0
        X3 = X1 + X2
        B3 = ((self.AC1 * 4.0 + X3) * (2 ** OSS) + 2.0) / 4.0

        X1 = (self.AC3 * B6) / 8192.0
        X2 = (self.B1 * (B6 * B6 / 4096.0)) / 65536.0
        X3 = (X1 + X2 + 2.0) / 4.0
        B4 = (self.AC4 * (X3 + 32768.0)) / 32768.0
        B7 = (UP - B3) * (50000.0 / (2 ** OSS))

        if B7 < 0x80000000:
            p = (B7 * 2.0) / B4
        else:
            p = (B7 / B4) * 2.0

        X1 = (p / 256.0) ** 2
        X1 = (X1 * 3038.0) / 65536.0
        X2 = (-7357.0 * p) / 65536.0
        p = p + (X1 + X2 + 3791.0) / 16.0

        pressure_pa = p  # in Pascals
        return temp_C, pressure_pa

    def read_altitude(self, sea_level_pa=101325.0):
        _, pressure = self.read_temperature_pressure()
        # International barometric formula
        altitude = 44330.0 * (1.0 - (pressure / sea_level_pa) ** (1.0 / 5.255))
        return altitude

if __name__ == "__main__":
    sensor = BMP180()

    print("BMP180 demo running... Ctrl+C to stop.")
    try:
        while True:
            temp_C, pressure_pa = sensor.read_temperature_pressure()
            altitude_m = sensor.read_altitude()

            print(f"Temperature: {temp_C:.2f} °C, "
                  f"Pressure: {pressure_pa/100:.2f} hPa, "
                  f"Altitude (approx): {altitude_m:.2f} m")

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nStopped.")
