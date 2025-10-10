import pigpio, sys, termios, tty
import json, socket # for ps4

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

    # UDP server (listen on all interfaces, port 5005)
    UDP_IP, UDP_PORT = "0.0.0.0", 5005
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(0.2)  # non-blocking-ish

    print(f"Listening for joystick on {UDP_PORT} (UDP). 'Stop' with Ctrl+C.")

    try:
        while True:
            try:
                data, _ = sock.recvfrom(256)
                msg = json.loads(data.decode("utf-8"))
                # Expect {"L": int(-100..100), "R": int(-100..100)} or {"stop":1}
                if "stop" in msg:
                    A.set_speed(0); B.set_speed(0)
                else:
                    L = int(max(-100, min(100, msg.get("L", 0))))
                    R = int(max(-100, min(100, msg.get("R", 0))))
                    A.set_speed(L); B.set_speed(R)
                print(f"\rA:{A.speed:+4d}%   B:{B.speed:+4d}% ", end="", flush=True)
            except socket.timeout:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        A.set_speed(0)
        B.set_speed(0)
        pi.stop()
        print("\nExiting.")

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

    # mode: which motors we adjust with w/s, arrows (1=A, 2=B, 3=both)
    # mode = 3

    # try:
    #     while True:
    #         ch = getch()
    #         if ch in ('q', 'Q'):
    #             break
    #         elif ch == '1':
    #             mode = 1; print("\nMode: A only")
    #         elif ch == '2':
    #             mode = 2; print("\nMode: B only")
    #         elif ch == '3':
    #             mode = 3; print("\nMode: Both")

    #         # Helper to set speeds by mode
    #         def set_by_mode(delta):
    #             if mode == 1:
    #                 A.set_speed(A.speed + delta)
    #             elif mode == 2:
    #                 B.set_speed(B.speed + delta)
    #             else:
    #                 A.set_speed(A.speed + delta)
    #                 B.set_speed(B.speed + delta)

    #         if ch == 'w':
    #             set_by_mode(+STEP)
    #         elif ch == 's':
    #             set_by_mode(-STEP)

    #         elif ch == 'x':
    #             A.set_speed(0); B.set_speed(0)
    #         elif ch == 'a':
    #             A.set_speed(A.speed - STEP)
    #             B.set_speed(B.speed + STEP)
    #         elif ch == 'd':
    #             A.set_speed(A.speed + STEP)
    #             B.set_speed(B.speed - STEP)
    #         elif ch == '\x1b[A':  # UP
    #             set_by_mode(+BIG_STEP)
    #         elif ch == '\x1b[B':  # DOWN
    #             set_by_mode(-BIG_STEP)
    #         elif ch == '\x1b[D':  # LEFT – spin left
    #             A.set_speed(A.speed - BIG_STEP)
    #             B.set_speed(B.speed + BIG_STEP)
    #         elif ch == '\x1b[C':  # RIGHT – spin right
    #             A.set_speed(A.speed + BIG_STEP)
    #             B.set_speed(B.speed - BIG_STEP)

    #         print(f"\rA:{A.speed:+4d}%   B:{B.speed:+4d}% ",
    #               end="", flush=True)

    # except KeyboardInterrupt:
    #     pass
    # finally:
    #     A.set_speed(0); B.set_speed(0)
    #     pi.stop()
    #     print("\nExiting.")


if __name__ == "__main__":
    main()
