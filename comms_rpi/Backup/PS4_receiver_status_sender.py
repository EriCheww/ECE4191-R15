import pigpio, sys, termios, tty, time
import json, socket # for ps4
import threading # for status

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

# --- status config ---
STATUS_INTERVAL = 1        # seconds
STATUS_UDP_PORT = 5051       # laptop port to receive status
last_host = {"ip": None}     # learned from joystick sender
FIRST_TIME_MESSAGE = False
FIRST_TIME_MESSAGE_1 = False

def stable_gpio_snapshot(pi, pins=range(2,28), exclude=()):
    """Return dict {pin: 0/1} where 1 means the pin reads high even with pull-down applied (for INPUTs).
       OUTPUT pins are reported as whatever they are currently driven to. Does not change OUTPUTs.
    """
    out = {}
    for p in pins:
        if p in exclude:  # e.g., keep 2/3 alone if I2C is in use
            out[p] = int(pi.read(p))
            continue

        mode = pi.get_mode(p)
        if mode == pigpio.INPUT:
            # Apply pull-down briefly so floating inputs bias low
            pi.set_pull_up_down(p, pigpio.PUD_DOWN)
            time.sleep(0.005)
            out[p] = int(pi.read(p))
            # Optional: clear pull afterwards
            pi.set_pull_up_down(p, pigpio.PUD_OFF)
        else:
            # For OUTPUT/ALT, just report current level
            out[p] = int(pi.read(p))
    return out


def status_payload(pi):
    pins = stable_gpio_snapshot(pi, exclude=(2,3))
    gpio_dict = {str(p): {"level": pins[p]} for p in pins}
    return {
        "ts": time.time(),
        "pi_connected": bool(pi.connected),
        "gpio": gpio_dict
    }


def status_thread(pi):
    global FIRST_TIME_MESSAGE_1
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        try:
            ip = last_host["ip"]
            if ip:
                payload = json.dumps(status_payload(pi)).encode("utf-8")
                sock.sendto(payload, (ip, STATUS_UDP_PORT))
                if not FIRST_TIME_MESSAGE_1:
                    print(f"System ready. Status packets sending to {ip}:{STATUS_UDP_PORT}, size {len(payload)} bytes, every {STATUS_INTERVAL}s")
                    FIRST_TIME_MESSAGE_1 = True
        except Exception:
            print("status_thread send error:", Exception)
        time.sleep(STATUS_INTERVAL)


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
    global FIRST_TIME_MESSAGE
    
    # Connect to pigpio
    pi = pigpio.pi()
    if not pi.connected:
        print("Start pigpio with: sudo systemctl start pigpiod")
        sys.exit(1)

    # Create motor drivers
    A = HBridge(pi, ENA, IN1, IN2)
    B = HBridge(pi, ENB, IN3, IN4)
    A.set_speed(START)
    B.set_speed(START)

    # --- Start periodic status sender (UDP push to laptop) ---
    # Requires: status_thread(pi) and global last_host dict
    threading.Thread(target=status_thread, args=(pi,), daemon=True).start()

    # --- Joystick UDP server (listen for control packets) ---
    UDP_IP, UDP_PORT = "0.0.0.0", 5005
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(0.2)  # non-blocking-ish

    print(f"Joystick: listening on UDP {UDP_PORT}. Ctrl+C to stop.")

    try:
        while True:
            try:
                # Receive joystick JSON: {"L":-100..100,"R":-100..100} or {"stop":1}
                data, addr = sock.recvfrom(256)
                last_host["ip"] = addr[0]   # learn laptop IP for status push
                # print("Learned host:", last_host["ip"])
                msg = json.loads(data.decode("utf-8"))

                if "stop" in msg:
                    A.set_speed(0)
                    B.set_speed(0)
                else:
                    L = int(max(-100, min(100, msg.get("L", 0))))
                    R = int(max(-100, min(100, msg.get("R", 0))))
                    A.set_speed(L)
                    B.set_speed(R)

                if not FIRST_TIME_MESSAGE:
                    print(f"Controll packets recieved!")
                    FIRST_TIME_MESSAGE = True
                # print(f"\rHost:{last_host['ip']}  A:{A.speed:+4d}%  B:{B.speed:+4d}% ",end="", flush=True)

            except socket.timeout:
                # No packet this tick; just loop
                pass
            except (ValueError, json.JSONDecodeError) as e:
                # Bad or partial JSON; ignore this packet
                print(f"\nBad joystick JSON: {e}")
            except Exception as e:
                # Log unexpected errors and keep running
                print(f"\nJoystick loop error: {e}")

    except KeyboardInterrupt:
        pass
    finally:
        try:
            A.set_speed(0)
            B.set_speed(0)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
        pi.stop()
        print("\nExiting.")

if __name__ == "__main__":
    main()
