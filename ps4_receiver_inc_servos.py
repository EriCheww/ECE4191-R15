#!/usr/bin/env python3
import pigpio, sys, time, json, socket

# ===== PIN MAP (BCM) =====
ENA = 12
IN1 = 16
IN2 = 20
ENB = 13
IN3 = 21
IN4 = 26
# =========================

PWM_FREQ = 1000        # Hz
WATCHDOG_S = 0.6       # stop motors if no packet in this many seconds

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

class HBridge:
    def __init__(self, pi, ena, in1, in2):
        self.pi, self.ena, self.in1, self.in2 = pi, ena, in1, in2
        for p in (ena, in1, in2):
            pi.set_mode(p, pigpio.OUTPUT)
        pi.set_PWM_frequency(ena, PWM_FREQ)
        pi.set_PWM_range(ena, 255)
        self.speed = 0   # -100..+100

    def apply(self):
        spd = int(abs(self.speed) * 255 / 100)
        if self.speed > 0:
            self.pi.write(self.in1, 1); self.pi.write(self.in2, 0)
            self.pi.set_PWM_dutycycle(self.ena, spd)
        elif self.speed < 0:
            self.pi.write(self.in1, 0); self.pi.write(self.in2, 1)
            self.pi.set_PWM_dutycycle(self.ena, spd)
        else:
            # brake (both high) with 0 PWM; change to both low if you prefer coast
            self.pi.write(self.in1, 1); self.pi.write(self.in2, 1)
            self.pi.set_PWM_dutycycle(self.ena, 0)

    def set_speed(self, pct):
        self.speed = clamp(pct, -100, 100)
        self.apply()

def main():
    pi = pigpio.pi()
    if not pi.connected:
        print("Start pigpio with: sudo systemctl start pigpiod")
        sys.exit(1)

    A = HBridge(pi, ENA, IN1, IN2)
    B = HBridge(pi, ENB, IN3, IN4)
    A.set_speed(0); B.set_speed(0)

    UDP_IP, UDP_PORT = "0.0.0.0", 5005
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(0.1)

    print(f"Listening on UDP {UDP_PORT}. Ctrl+C to stop.")
    last_pkt = time.time()

    try:
        while True:
            try:
                data, _ = sock.recvfrom(256)
                msg = json.loads(data.decode("utf-8"))

                if "stop" in msg:
                    A.set_speed(0); B.set_speed(0)
                else:
                    L = int(clamp(msg.get("L", 0), -100, 100))
                    R = int(clamp(msg.get("R", 0), -100, 100))
                    A.set_speed(L); B.set_speed(R)

                last_pkt = time.time()
                print(f"\rA:{A.speed:+4d}%   B:{B.speed:+4d}% ", end="", flush=True)

            except socket.timeout:
                # Watchdog: if no packets recently, stop motors for safety
                if time.time() - last_pkt > WATCHDOG_S:
                    if A.speed != 0 or B.speed != 0:
                        A.set_speed(0); B.set_speed(0)
                        print("\rA:+000%   B:+000%  (watchdog) ", end="", flush=True)
                # loop
                pass

    except KeyboardInterrupt:
        pass
    finally:
        A.set_speed(0); B.set_speed(0)
        pi.stop()
        print("\nExiting.")

if __name__ == "__main__":
    main()
