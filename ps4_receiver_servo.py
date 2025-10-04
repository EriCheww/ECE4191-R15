#!/usr/bin/env python3
import pigpio, sys, time, json, socket

# ===== DC Motor PIN MAP (BCM) =====
ENA = 12
IN1 = 16
IN2 = 20
ENB = 13
IN3 = 21
IN4 = 26
PWM_FREQ = 1000

# ===== Servo PIN MAP =====
PIN_SG90 = 24   # positional servo (Square/Circle)
PIN_MG90 = 23   # positional servo (Triangle/X)

# ===== Servo settings =====
MIN_DEG, MAX_DEG = 0, 180
step_deg = 5
sg90_deg = 90
mg90_deg = 90

def angle_to_us(angle):
    return int(500 + (angle/180.0)*1900)  # 500–2400 µs typical range

def clamp(v, lo, hi): return lo if v < lo else hi if v > hi else v

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
        self.speed = clamp(pct, -100, 100)
        self.apply()

def main():
    global sg90_deg, mg90_deg
    pi = pigpio.pi()
    if not pi.connected:
        print("Start pigpio with: sudo systemctl start pigpiod")
        sys.exit(1)

    # Setup motors
    A = HBridge(pi, ENA, IN1, IN2)
    B = HBridge(pi, ENB, IN3, IN4)
    A.set_speed(0); B.set_speed(0)

    # Setup servos
    pi.set_mode(PIN_SG90, pigpio.OUTPUT)
    pi.set_mode(PIN_MG90, pigpio.OUTPUT)
    pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(sg90_deg))
    pi.set_servo_pulsewidth(PIN_MG90, angle_to_us(mg90_deg))

    # UDP server
    UDP_IP, UDP_PORT = "0.0.0.0", 5005
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(0.2)

    print(f"Listening for joystick+button on {UDP_PORT}")

    try:
        while True:
            try:
                data, _ = sock.recvfrom(256)
                msg = json.loads(data.decode("utf-8"))

                # Motors
                if "stop" in msg:
                    A.set_speed(0); B.set_speed(0)
                else:
                    L = int(clamp(msg.get("L", 0), -100, 100))
                    R = int(clamp(msg.get("R", 0), -100, 100))
                    A.set_speed(L); B.set_speed(R)

                # Servos via button presses
                # Expect booleans or 1/0 in msg["square"], msg["circle"], msg["triangle"], msg["cross"]
                if msg.get("square"):   # SG90 decrease angle
                    sg90_deg = clamp(sg90_deg - step_deg, MIN_DEG, MAX_DEG)
                    pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(sg90_deg))
                if msg.get("circle"):   # SG90 increase angle
                    sg90_deg = clamp(sg90_deg + step_deg, MIN_DEG, MAX_DEG)
                    pi.set_servo_pulsewidth(PIN_SG90, angle_to_us(sg90_deg))
                if msg.get("triangle"): # MG90 increase angle
                    mg90_deg = clamp(mg90_deg + step_deg, MIN_DEG, MAX_DEG)
                    pi.set_servo_pulsewidth(PIN_MG90, angle_to_us(mg90_deg))
                if msg.get("cross"):    # MG90 decrease angle
                    mg90_deg = clamp(mg90_deg - step_deg, MIN_DEG, MAX_DEG)
                    pi.set_servo_pulsewidth(PIN_MG90, angle_to_us(mg90_deg))

                print(f"\rA:{A.speed:+4d}% B:{B.speed:+4d}% | SG90:{sg90_deg}° MG90:{mg90_deg}°", 
                      end="", flush=True)

            except socket.timeout:
                pass

    except KeyboardInterrupt:
        pass
    finally:
        A.set_speed(0); B.set_speed(0)
        pi.set_servo_pulsewidth(PIN_SG90, 0)
        pi.set_servo_pulsewidth(PIN_MG90, 0)
        pi.stop()
        print("\nExiting.")

if __name__ == "__main__":
    main()
