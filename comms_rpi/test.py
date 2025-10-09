import pigpio, sys, termios, tty, time
import json, socket
import threading

# ===== DC Motor PIN MAP (BCM) =====
ENA = 12   # was 18
IN1 = 16
IN2 = 20
ENB = 13   # was 19
IN3 = 21
IN4 = 26

PWM_FREQ = 1000   # Hz (1 kHz is safe for L298N)

# ===== Servo PIN MAP (from ps4_receiver_with_servo.py) =====
PIN_SG90 = 24   # positional servo (Square/Circle)
PIN_MG90 = 23   # positional servo (Triangle/Cross)

# ===== Servo settings (from ps4_receiver_with_servo.py) =====
MIN_DEG, MAX_DEG = 0, 180
STEP_DEG = 5
sg90_deg = 90
mg90_deg = 90

def angle_to_us(angle):
    # 500–2400 µs typical range (same formula as ps4_receiver_with_servo.py)
    return int(500 + (angle / 180.0) * 1900)

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

# --- status config ---
STATUS_INTERVAL = 1          # seconds
STATUS_UDP_PORT = 5051       # laptop port to receive status
last_host = {"ip": None}     # learned from joystick sender
FIRST_TIME_MESSAGE = False
FIRST_TIME_MESSAGE_1 = False

def stable_gpio_snapshot(pi, pins=range(2,28), exclude=()):
    """Return dict {pin: 0/1} with gentle biasing for floating inputs."""
    out = {}
    for p in pins:
        if p in exclude:
            out[p] = int(pi.read(p))
            continue
        mode = pi.get_mode(p)
        if mode == pigpio.INPUT:
            pi.set_pull_up_down(p, pigpio.PUD_DOWN)
            time.sleep(0.005)
            out[p] = int(pi.read(p))
            pi.set_pull_up_down(p, pigpio.PUD_OFF)
        else:
            out[p] = int(pi.read(p))
    return out

def status_payload(pi):
    # Add servo angles to your existing GPIO + connectivity status
    pins = stable_gpio_snapshot(pi, exclude=(2,3))
    gpio_dict = {str(p): {"level": pins[p]} for p in pins}
    return {
        "ts": time.time(),
        "pi_connected": bool(pi.connected),
        "gpio": gpio_dict,
        "servo": {
            "sg90_deg": sg90_deg,
            "mg90_deg": mg90_deg,
        }
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
        except Exception as e:
            print("status_thread send error:", repr(e))
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

def clamp_speed(v): return clamp(v, -100, 100)

class HBridge:
    def __init__(self, pi, ena, in1, in2):
        self.pi, self.ena, self.in1, self.in2 = pi, ena, in1, in2
        for p in (ena, in1, in2):
            pi.set_mode(p, pigpio.OUTPUT)
        pi.set_PWM_frequency(ena, PWM_FREQ)
        pi.set_PWM_range(ena, 255)
        self.speed = 0

    def apply(self):
        spd = int(abs(self.speed) * 255 / 100)
        if self.speed > 0:
            self.pi.write(self.in1, 1); self.pi.write(self.in2, 0)
            self.pi.set_PWM_dutycycle(self.ena, spd)
        elif self.speed < 0:
            self.pi.write(self.in1, 0); self.pi.write(self.in2, 1)
            self.pi.set_PWM_dutycycle(self.ena, spd)
        else:
            self.pi.write(self.in1, 1); self.pi.write(self.in2, 1)
            self.pi.set_PWM_dutycycle(self.ena, 0)

    def set_speed(self, pct):
        self.speed = clamp_speed(pct)
        self.apply()

def main():
    global FIRST_TIME_MESSAGE, sg90_deg, mg90_deg

    # Connect to pigpio
    pi = pigpio.pi()
    if not pi.connected:
        print("Start pigpio with: sudo systemctl start pigpiod")
        sys.exit(1)

    # Create motor drivers
    A = HBridge(pi, ENA, IN1, IN2)
    B = HBridge(pi, ENB, IN3, IN4)
    A.set_speed(0)
    B.set_speed(0)

    # --- Setup servos (mirrors ps4_receiver_with_servo.py) ---
    pi.set_mode(PIN_SG90, pigpio.OUTPUT)
    pi.set_mode(PIN_MG90, pigpio.OUTPUT)
    pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(sg90_deg))
    pi.set_servo_pulsewidth(PIN_MG90, angle_to_us(mg90_deg))

    # --- Start periodic status sender (UDP push to laptop) ---
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
                # Receive joystick JSON:
                # {"L":-100..100,"R":-100..100, "square":0/1, "circle":0/1, "triangle":0/1, "cross":0/1}
                # or {"stop":1}
                data, addr = sock.recvfrom(256)
                last_host["ip"] = addr[0]   # learn laptop IP for status push
                msg = json.loads(data.decode("utf-8"))

                # Motors
                if "stop" in msg:
                    A.set_speed(0)
                    B.set_speed(0)
                else:
                    L = int(clamp_speed(msg.get("L", 0)))
                    R = int(clamp_speed(msg.get("R", 0)))
                    A.set_speed(L)
                    B.set_speed(R)

                # ---- Servo buttons (exact behaviour from ps4_receiver_with_servo.py) ----
                # Square/Circle adjust SG90; Triangle/Cross adjust MG90, by STEP_DEG each press.
                if msg.get("square"):   # SG90 decrease
                    sg90_deg = clamp(sg90_deg - STEP_DEG, MIN_DEG, MAX_DEG)
                    pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(sg90_deg))
                if msg.get("circle"):   # SG90 increase
                    sg90_deg = clamp(sg90_deg + STEP_DEG, MIN_DEG, MAX_DEG)
                    pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(sg90_deg))
                if msg.get("triangle"): # MG90 increase
                    mg90_deg = clamp(mg90_deg + STEP_DEG, MIN_DEG, MAX_DEG)
                    pi.set_servo_pulsewidth(PIN_MG90, angle_to_us(mg90_deg))
                if msg.get("cross"):    # MG90 decrease
                    mg90_deg = clamp(mg90_deg - STEP_DEG, MIN_DEG, MAX_DEG)
                    pi.set_servo_pulsewidth(PIN_MG90, angle_to_us(mg90_deg))

                if not FIRST_TIME_MESSAGE:
                    print("Control packets received!")
                    FIRST_TIME_MESSAGE = True

                # Optional: live console HUD
                # print(f"\rHost:{last_host['ip']}  A:{A.speed:+4d}%  B:{B.speed:+4d}%  SG90:{sg90_deg:3d}°  MG90:{mg90_deg:3d}°",
                #       end="", flush=True)

            except socket.timeout:
                # No packet this tick; just loop
                pass
            except (ValueError, json.JSONDecodeError) as e:
                print(f"\nBad joystick JSON: {e}")
            except Exception as e:
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
            pi.set_servo_pulsewidth(PIN_SG90, 0)
            pi.set_servo_pulsewidth(PIN_MG90, 0)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
        pi.stop()
        print("\nExiting.")
