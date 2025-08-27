import pigpio, sys, termios, tty, time

# --- PS4 / pygame support ---
try:
    import pygame
    HAVE_PYGAME = True
except ImportError:
    HAVE_PYGAME = False

DEADZONE = 0.12  # ignore tiny stick noise

# SDL/pygame typical DS4 mappings on Raspberry Pi.
AX_LX = 0   # left stick X (turn left/right)
AX_LY = 1   # left stick Y (throttle forward/back)  NOTE: up is -1.0
BTN_CROSS = 1   # X button -> stop
BTN_TRI   = 3   # Triangle -> mode: both
BTN_L1    = 4   # L1 -> mode: A only
BTN_R1    = 5   # R1 -> mode: B only
BTN_OPTIONS = 9 # Options -> quit


# ===== PIN MAP (BCM) =====
ENA = 12   # was 18
IN1 = 16
IN2 = 20

ENB = 13   # was 19
IN3 = 21
IN4 = 26
# =========================

PWM_FREQ = 1000   # Hz (1 kHz is safe for L298N)
STEP = 10         # % speed step per keypress
BIG_STEP = 25     # % speed step for arrows
START = 0         # start stopped


def getch():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch += sys.stdin.read(2)  # arrows
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class HBridge:
    def __init__(self, pi, ena, in1, in2):
        self.pi, self.ena, self.in1, self.in2 = pi, ena, in1, in2
        for p in (ena, in1, in2):
            pi.set_mode(p, pigpio.OUTPUT)
        # Set PWM frequency and full range (0..255)
        pi.set_PWM_frequency(ena, PWM_FREQ)
        pi.set_PWM_range(ena, 255)
        self.speed = 0   # -100..+100

    def apply(self):
        spd = int(abs(self.speed) * 255 / 100)
        if self.speed > 0:
            # Forward: IN1=H, IN2=L
            self.pi.write(self.in1, 1)
            self.pi.write(self.in2, 0)
            self.pi.set_PWM_dutycycle(self.ena, spd)
        elif self.speed < 0:
            # Reverse: IN1=L, IN2=H
            self.pi.write(self.in1, 0)
            self.pi.write(self.in2, 1)
            self.pi.set_PWM_dutycycle(self.ena, spd)
        else:
            # Brake or coast: choose one
            # Brake: IN1=H, IN2=H with 0 PWM
            self.pi.write(self.in1, 1)
            self.pi.write(self.in2, 1)
            self.pi.set_PWM_dutycycle(self.ena, 0)

    def set_speed(self, pct):  # -100..+100
        self.speed = clamp(pct, -100, 100)
        self.apply()


def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("Start pigpio with: sudo systemctl start pigpiod")
        sys.exit(1)

    A = HBridge(pi, ENA, IN1, IN2)
    B = HBridge(pi, ENB, IN3, IN4)
    A.set_speed(START)
    B.set_speed(START)

    print(
        "L298N DC motor test\n"
    )

    print(
        "L298N DC motor test\n"
        "Controls:\n"
        "  w/s : both motors +/- speed\n"
        "  a/d : steer (A- / B- and A+ / B+)\n"
        "  Arrow ↑/↓ : big +/- to both\n"
        "  Arrow ←/→ : spin in place (A-/B+ and A+/B-)\n"
        "  x : stop (brake)\n"
        "  1/2 : test A/B solo (toggle), 3: both\n"
        "  q : quit\n"
    )

        # --- ADD: Initialize PS4 controller if pygame is available ---
    js = None
    if HAVE_PYGAME:
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            js = pygame.joystick.Joystick(0)
            js.init()
            print(f"PS4 controller detected: {js.get_name()}")
            print("Use Left Stick (LY=throttle, LX=turn). "
                  "L1: A-only, R1: B-only, Triangle: both, X: stop, Options: quit")
        else:
            print("No joystick found; falling back to keyboard controls.")

    # mode: which motors we adjust with w/s, arrows (1=A, 2=B, 3=both)
    mode = 3

    try:
        # while True:
        #     ch = getch()
        #     if ch in ('q', 'Q'):
        #         break
        #     elif ch == '1':
        #         mode = 1; print("\nMode: A only")
        #     elif ch == '2':
        #         mode = 2; print("\nMode: B only")
        #     elif ch == '3':
        #         mode = 3; print("\nMode: Both")

        #     # Helper to set speeds by mode
        #     def set_by_mode(delta):
        #         if mode == 1:
        #             A.set_speed(A.speed + delta)
        #         elif mode == 2:
        #             B.set_speed(B.speed + delta)
        #         else:
        #             A.set_speed(A.speed + delta)
        #             B.set_speed(B.speed + delta)

        #     if ch == 'w':
        #         set_by_mode(+STEP)
        #     elif ch == 's':
        #         set_by_mode(-STEP)

        #     elif ch == 'x':
        #         A.set_speed(0); B.set_speed(0)
        #     elif ch == 'a':
        #         A.set_speed(A.speed - STEP)
        #         B.set_speed(B.speed + STEP)
        #     elif ch == 'd':
        #         A.set_speed(A.speed + STEP)
        #         B.set_speed(B.speed - STEP)
        #     elif ch == '\x1b[A':  # UP
        #         set_by_mode(+BIG_STEP)
        #     elif ch == '\x1b[B':  # DOWN
        #         set_by_mode(-BIG_STEP)
        #     elif ch == '\x1b[D':  # LEFT – spin left
        #         A.set_speed(A.speed - BIG_STEP)
        #         B.set_speed(B.speed + BIG_STEP)
        #     elif ch == '\x1b[C':  # RIGHT – spin right
        #         A.set_speed(A.speed + BIG_STEP)
        #         B.set_speed(B.speed - BIG_STEP)

        #     print(f"\rA:{A.speed:+4d}%   B:{B.speed:+4d}% ",
        #           end="", flush=True)
        while True:
            # Prefer controller if present, else keyboard
            if js is not None:
                # Pump events so pygame updates state
                pygame.event.pump()

                # --- Modes (buttons) ---
                if js.get_button(BTN_L1):
                    mode = 1
                elif js.get_button(BTN_R1):
                    mode = 2
                elif js.get_button(BTN_TRI):
                    mode = 3
                if js.get_button(BTN_CROSS):
                    A.set_speed(0); B.set_speed(0)
                if js.get_button(BTN_OPTIONS):
                    break

                # --- Axes → differential drive ---
                lx = js.get_axis(AX_LX)
                ly = js.get_axis(AX_LY)

                # Deadzone
                lx = 0 if abs(lx) < DEADZONE else lx
                ly = 0 if abs(ly) < DEADZONE else ly

                # Convert to percentage speeds (-100..+100)
                throttle = int(clamp(-ly, -1.0, 1.0) * 100)  # up on stick = forward
                turn     = int(clamp( lx, -1.0, 1.0) * 100)

                # Differential mixing
                left_cmd  = clamp(throttle - turn, -100, 100)
                right_cmd = clamp(throttle + turn, -100, 100)

                # Apply by mode (reuse existing semantics)
                if mode == 1:        # A only
                    A.set_speed(left_cmd)
                elif mode == 2:      # B only
                    B.set_speed(right_cmd)
                else:                # both (default)
                    A.set_speed(left_cmd)
                    B.set_speed(right_cmd)

            else:
                # --- ORIGINAL KEYBOARD PATH (unchanged) ---
                ch = getch()
                if ch in ('q', 'Q'):
                    break
                elif ch == '1':
                    mode = 1; print("\nMode: A only")
                elif ch == '2':
                    mode = 2; print("\nMode: B only")
                elif ch == '3':
                    mode = 3; print("\nMode: Both")

                def set_by_mode(delta):
                    if mode == 1:
                        A.set_speed(A.speed + delta)
                    elif mode == 2:
                        B.set_speed(B.speed + delta)
                    else:
                        A.set_speed(A.speed + delta)
                        B.set_speed(B.speed + delta)

                if ch == 'w':
                    set_by_mode(+STEP)
                elif ch == 's':
                    set_by_mode(-STEP)
                elif ch == 'x':
                    A.set_speed(0); B.set_speed(0)
                elif ch == 'a':
                    A.set_speed(A.speed - STEP)
                    B.set_speed(B.speed + STEP)
                elif ch == 'd':
                    A.set_speed(A.speed + STEP)
                    B.set_speed(B.speed - STEP)
                elif ch == '\x1b[A':  # UP
                    set_by_mode(+BIG_STEP)
                elif ch == '\x1b[B':  # DOWN
                    set_by_mode(-BIG_STEP)
                elif ch == '\x1b[D':  # LEFT – spin left
                    A.set_speed(A.speed - BIG_STEP)
                    B.set_speed(B.speed + BIG_STEP)
                elif ch == '\x1b[C':  # RIGHT – spin right
                    A.set_speed(A.speed + BIG_STEP)
                    B.set_speed(B.speed - BIG_STEP)

            print(f"\rA:{A.speed:+4d}%   B:{B.speed:+4d}% ", end="", flush=True)


    except KeyboardInterrupt:
        pass
    finally:
        A.set_speed(0); B.set_speed(0)
        pi.stop()
        print("\nExiting.")


if __name__ == "__main__":
    main()
