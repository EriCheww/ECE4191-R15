import pigpio, sys, termios, tty, time
import json, socket # for ps4
import glob, os, subprocess, threading # for status

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
STATUS_INTERVAL = 1.0        # seconds
STATUS_UDP_PORT = 5051       # laptop port to receive status
last_host = {"ip": None}     # learned from joystick sender

def _mode_name(m):
    return {
        pigpio.INPUT: "INPUT",
        pigpio.OUTPUT: "OUTPUT",
        pigpio.ALT0: "ALT0",
        pigpio.ALT1: "ALT1",
        pigpio.ALT2: "ALT2",
        pigpio.ALT3: "ALT3",
        pigpio.ALT4: "ALT4",
        pigpio.ALT5: "ALT5"
    }.get(m, str(m))


def list_devices():
    """Enumerate useful device nodes and USBs to see what's present."""
    def _ls(pattern):
        return sorted(glob.glob(pattern))

    info = {
        "gpiochips": _ls("/dev/gpiochip*"),
        "i2c_buses": _ls("/dev/i2c-*"),
        "spi_devices": _ls("/dev/spidev*"),
        "serial_ttys": [p for p in _ls("/dev/tty*") if any(k in p for k in ("AMA", "S", "USB", "ACM"))],
        "video": _ls("/dev/video*"),
        "usb_lsusb": []
    }
    try:
        out = subprocess.run(["lsusb"], capture_output=True, text=True, check=False)
        if out.stdout:
            info["usb_lsusb"] = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    except Exception as e:
        info["usb_lsusb"] = [f"(lsusb unavailable: {e})"]

    return info

def status_payload(pi):
    return {
        "ts": time.time(),
        "pigpio_connected": bool(pi.connected),
        "gpio": {
            str(p): {
                "mode": _mode_name(pi.get_mode(p)),
                "level": int(pi.read(p)),
                "duty": (pi.get_PWM_dutycycle(p) if p in (ENA, ENB) else None)
            }
            for p in (ENA, IN1, IN2, ENB, IN3, IN4)
        },
        "devices": list_devices()
    }

def status_thread(pi):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        try:
            ip = last_host["ip"]
            if ip:
                payload = json.dumps(status_payload(pi)).encode("utf-8")
                sock.sendto(payload, (ip, STATUS_UDP_PORT))
        except Exception:
            pass
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
                msg = json.loads(data.decode("utf-8"))

                if "stop" in msg:
                    A.set_speed(0)
                    B.set_speed(0)
                else:
                    L = int(max(-100, min(100, msg.get("L", 0))))
                    R = int(max(-100, min(100, msg.get("R", 0))))
                    A.set_speed(L)
                    B.set_speed(R)

                print(f"\rHost:{last_host['ip']}  A:{A.speed:+4d}%  B:{B.speed:+4d}% ",
                      end="", flush=True)

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
