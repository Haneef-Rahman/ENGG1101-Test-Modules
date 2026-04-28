import time
from gpiozero import LED, Buzzer

# BCM GPIO pins
RED_PIN = 25
BUZZER_PIN = 21

red = LED(RED_PIN)
alarm = Buzzer(BUZZER_PIN)

def alarm_loop(on_led=0.5, off_led=0.5, buzz_on=0.2, buzz_off=0.8):
    # blink LED in background
    red.blink(on_time=on_led, off_time=off_led, n=None, background=True)

    try:
        while True:
            alarm.on()
            time.sleep(buzz_on)
            alarm.off()
            time.sleep(buzz_off)
    except KeyboardInterrupt:
        pass
    finally:
        red.off()
        alarm.off()
        red.close()
        alarm.close()

if __name__ == "__main__":
    alarm_loop()
