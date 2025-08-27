import RPi.GPIO as GPIO
import time

# BCM pin numbers
TRIG = 23   # your TRIG on GPIO 24
ECHO = 24   # your ECHO on GPIO 23 (use a voltage divider to 3.3V!)

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def get_distance_cm(timeout=0.03):
    """
    Returns distance in cm, or None on timeout.
    timeout is per phase (waiting for echo rise/fall).
    """
    # settle the sensor
    GPIO.output(TRIG, False)
    time.sleep(0.05)

    # 10µs trigger pulse
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    # wait for ECHO to go HIGH (start)
    start_time = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if pulse_start - start_time > timeout:
            return None

    # wait for ECHO to go LOW (end)
    start_time = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if pulse_end - start_time > timeout:
            return None

    pulse_duration = pulse_end - pulse_start
    # distance (cm) = time * speed_of_sound/2; ~34300 cm/s -> /2 = 17150
    distance_cm = pulse_duration * 17150.0
    return round(distance_cm, 2)

try:
    input("Press Enter to START ultrasonic readings (Ctrl+C to stop)...\n")
    print("Measuring... (Ctrl+C to stop)")
    while True:
        d = get_distance_cm()
        if d is None:
            print("No echo (timeout). Check wiring/aim.", flush=True)
        else:
            print(f"Distance: {d} cm", flush=True)
        time.sleep(0.25)  # ~4 readings/sec

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    GPIO.cleanup()
