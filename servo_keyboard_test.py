#!/usr/bin/env python3
import pigpio, curses, time

# === Editable pins (BCM) ===
PIN_FS90R = 16   # FS90R (continuous rotation)
PIN_SG90  = 18   # SG90 (positional)

# === FS90R settings ===
NEUTRAL_US = 1500          # stop
STEP_US = 25               # speed increment per keypress
MIN_US, MAX_US = 1000, 2000
fs90r_us = NEUTRAL_US

# === SG90 settings ===
MIN_DEG, MAX_DEG = 0, 180
deg = 90                   # start centered

def angle_to_us(angle):
    # Typical SG90 range ~500–2400 µs for 0–180°
    # Adjust if your horn hits limits (try 500–2400 or 600–2400)
    return int(500 + (angle/180.0)*1900)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def main(stdscr):
    global fs90r_us, deg
    pi = pigpio.pi()
    if not pi.connected:
        raise RuntimeError("pigpio daemon not running. Start with: sudo systemctl start pigpiod")

    # Initialise outputs
    pi.set_mode(PIN_FS90R, pigpio.OUTPUT)
    pi.set_mode(PIN_SG90, pigpio.OUTPUT)
    pi.set_servo_pulsewidth(PIN_FS90R, NEUTRAL_US)   # stop FS90R
    pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(deg))

    # Curses setup
    stdscr.nodelay(True)
    curses.cbreak()
    stdscr.keypad(True)
    curses.noecho()
    stdscr.clear()
    stdscr.addstr(0, 0, "FS90R: Up/Down = speed, 's' stop | SG90: Left/Right = angle, 'r' center | 'q' quit")
    stdscr.refresh()

    try:
        while True:
            key = stdscr.getch()
            if key == curses.ERR:
                time.sleep(0.01)
                continue

            if key == curses.KEY_UP:
                fs90r_us = clamp(fs90r_us + STEP_US, MIN_US, MAX_US)
                pi.set_servo_pulsewidth(PIN_FS90R, fs90r_us)
            elif key == curses.KEY_DOWN:
                fs90r_us = clamp(fs90r_us - STEP_US, MIN_US, MAX_US)
                pi.set_servo_pulsewidth(PIN_FS90R, fs90r_us)
            elif key == curses.KEY_LEFT:
                deg = clamp(deg - 5, MIN_DEG, MAX_DEG)
                pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(deg))
            elif key == curses.KEY_RIGHT:
                deg = clamp(deg + 5, MIN_DEG, MAX_DEG)
                pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(deg))
            elif key in (ord('s'), ord('S')):
                fs90r_us = NEUTRAL_US
                pi.set_servo_pulsewidth(PIN_FS90R, fs90r_us)
            elif key in (ord('r'), ord('R')):
                deg = 90
                pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(deg))
            elif key in (ord('q'), ord('Q')):
                break

            stdscr.move(2, 0)
            stdscr.clrtoeol()
            stdscr.addstr(2, 0, f"FS90R pulse: {fs90r_us} us   |   SG90 angle: {deg}°   (q to quit)")
            stdscr.refresh()

    finally:
        # Safe shutdown
        pi.set_servo_pulsewidth(PIN_FS90R, NEUTRAL_US)  # stop rotation
        pi.set_servo_pulsewidth(PIN_SG90, 0)            # release SG90 pulses
        pi.stop()
        # restore terminal
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()

if __name__ == "__main__":
    curses.wrapper(main)
