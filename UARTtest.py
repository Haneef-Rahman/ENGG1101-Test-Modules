import serial, struct, time

def valid(frame):
    # sum of bytes 0..29 must equal the 16-bit value in bytes 30-31
    return (sum(frame[:-2]) & 0xFFFF) == struct.unpack('>H', frame[-2:])[0]

with serial.Serial('/dev/serial0', 9600, timeout=2) as ser:
    while True:
        if ser.read(1) != b'\x42':          # header 1
            continue
        if ser.read(1) != b'\x4D':          # header 2
            continue
        frame = ser.read(30)                # remaining bytes
        if len(frame) != 30 or not valid(b'\x42\x4D' + frame):
            print('Bad frame')              # checksum or length error
            continue

        pm1_0, pm2_5, pm10 = struct.unpack('>HHH', frame[2:8])
        print(f'PM1.0={pm1_0}  PM2.5={pm2_5}  PM10={pm10} µg/m³')
        time.sleep(1)
