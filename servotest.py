#!/usr/bin/env python3
import time
import pigpio

SERVO_GPIO = 18   # GPIO pin your servo signal is connected to

# Typical micro servo: 500–2400 µs
MID_PULSE = 1500  # center position

pi = pigpio.pi()
if not pi.connected:
    print("pigpio not running. Try: sudo systemctl start pigpiod")
    exit()

# Move servo to center (or change MID_PULSE to 500 or 2400 for other positions)
pi.set_servo_pulsewidth(SERVO_GPIO, MID_PULSE)
print("Servo ON at position for 5 seconds...")
time.sleep(5)

# Stop pulses (servo relaxes)
pi.set_servo_pulsewidth(SERVO_GPIO, 0)
pi.stop()
print("Servo OFF")
