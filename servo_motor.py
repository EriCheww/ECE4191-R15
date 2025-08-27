#!/usr/bin/env python3
import pigpio, time, sys, termios, tty

# ===== USER SETTINGS =====
SERVO_GPIO = 23          # BCM pin for servo signal
MIN_US = 500             # lower pulse bound (µs) ~0°
MAX_US = 2500            # upper pulse bound (µs) ~180°
STEP_SMALL = 5           # degrees per LEFT/RIGHT
STEP_BIG = 15            # degrees per UP/DOWN
START_DEG = 90           # start at centre
# =========================

def angle_to_us(deg):
    deg = max(0, min(180, deg))
    return int(MIN_US + (MAX_US - MIN_US) * (deg / 180.0))

def getch():
    """Read a single keypress (incl. arrow keys) without Enter."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':           # possible arrow key
            ch += sys.stdin.read(2)
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("pigpio daemon not running. Start with: sudo systemctl start pigpiod")
        sys.exit(1)

    pi.set_mode(SERVO_GPIO, pigpio.OUTPUT)
    angle = START_DEG
    pi.set_servo_pulsewidth(SERVO_GPIO, angle_to_us(angle))

    print(
        "Servo test on GPIO %d\n"
        "Controls:\n"
        "  ← / →  : -%d° / +%d°\n"
        "  ↑ / ↓  : -%d° / +%d°\n"
        "  c      : centre (90°)\n"
        "  s      : stop pulses (release servo)\n"
        "  q      : quit\n" %
        (SERVO_GPIO, STEP_SMALL, STEP_SMALL, STEP_BIG, STEP_BIG)
    )

    try:
        while True:
            ch = getch()
            if ch in ('q', 'Q'):
                break
            elif ch == 'c':
                angle = 90
            elif ch == 's':
                pi.set_servo_pulsewidth(SERVO_GPIO, 0)  # stop PWM
                print("Stopped (no holding torque). Press any key to resume.")
                getch()
                # resume at last angle
            elif ch == '\x1b[D':     # LEFT
                angle -= STEP_SMALL
            elif ch == '\x1b[C':     # RIGHT
                angle += STEP_SMALL
            elif ch == '\x1b[A':     # UP
                angle += STEP_BIG
            elif ch == '\x1b[B':     # DOWN
                angle -= STEP_BIG

            angle = max(0, min(180, angle))
            us = angle_to_us(angle)
            pi.set_servo_pulsewidth(SERVO_GPIO, us)
            print(f"\rAngle: {angle:3d}°  Pulse: {us} µs   ", end="", flush=True)

    except KeyboardInterrupt:
        pass
    finally:
        pi.set_servo_pulsewidth(SERVO_GPIO, 0)  # release
        pi.stop()
        print("\nExiting.")

if __name__ == "__main__":
    main()
