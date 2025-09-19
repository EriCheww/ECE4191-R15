#!/usr/bin/env python3
import json, socket, time, pygame

PI_IP   = "192.168.137.226"   # <-- set your Pi’s IP here
PI_PORT = 5005

SEND_HZ     = 30.0            # transmit rate
DEFAULT_SPD = 60              # % speed used when a D-pad direction is held
SPD_STEP    = 10              # % change when L1/R1 pressed
SPD_MIN     = 10
SPD_MAX     = 100

BTN_CROSS   = 1               # emergency stop (adjust if your mapping differs)
BTN_L1      = 4               # decrease base speed
BTN_R1      = 5               # increase base speed
BTN_OPTIONS = 9               # quit

def clamp(v, lo, hi): return max(lo, min(hi, v))

def main():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No joystick found."); return
    js = pygame.joystick.Joystick(0); js.init()
    print(f"Using: {js.get_name()} (hats={js.get_numhats()}, buttons={js.get_numbuttons()})")

    sock   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    period = 1.0 / SEND_HZ
    last_tx = 0.0

    base_spd = DEFAULT_SPD  # % used while holding a D-pad direction
    hat_x, hat_y = 0, 0     # current hat state (-1/0/1, -1/0/1)

    print("Controls:")
    print("  D-pad UP/DOWN  : forward/reverse at current base speed")
    print("  D-pad LEFT/RIGHT: spin in place left/right at base speed")
    print(f"  L1/R1          : -/+ {SPD_STEP}% base speed   (range {SPD_MIN}-{SPD_MAX}%)")
    print("  CROSS (X)      : emergency stop")
    print("  OPTIONS        : quit\n")

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.JOYHATMOTION:
                    hat_x, hat_y = event.value  # tuple (-1..1, -1..1)

                if event.type == pygame.JOYBUTTONDOWN:
                    b = event.button
                    if b == BTN_OPTIONS:
                        return
                    elif b == BTN_CROSS:
                        # immediate stop message
                        sock.sendto(json.dumps({"stop": 1}).encode("utf-8"), (PI_IP, PI_PORT))
                    elif b == BTN_L1:
                        base_spd = clamp(base_spd - SPD_STEP, SPD_MIN, SPD_MAX)
                    elif b == BTN_R1:
                        base_spd = clamp(base_spd + SPD_STEP, SPD_MIN, SPD_MAX)

            # Convert hat to differential L/R (priority: Y movement over X)
            if   hat_y == 1:   # UP (forward)
                L =  base_spd
                R =  base_spd
            elif hat_y == -1:  # DOWN (reverse)
                L = -base_spd
                R = -base_spd
            elif hat_x == -1:  # LEFT spin (CCW)
                L = -base_spd
                R =  base_spd
            elif hat_x == 1:   # RIGHT spin (CW)
                L =  base_spd
                R = -base_spd
            else:
                L = 0
                R = 0

            now = time.time()
            if now - last_tx >= period:
                msg = json.dumps({"L": int(L), "R": int(R)}).encode("utf-8")
                sock.sendto(msg, (PI_IP, PI_PORT))
                last_tx = now

            # light status
            print(f"\rHat=({hat_x:+d},{hat_y:+d})  Base={base_spd:3d}%  L/R=({L:+4d},{R:+4d})   ", end="", flush=True)
            time.sleep(0.001)

    except KeyboardInterrupt:
        pass
    finally:
        # send final stop
        try:
            sock.sendto(json.dumps({"stop": 1}).encode("utf-8"), (PI_IP, PI_PORT))
        except Exception:
            pass

if __name__ == "__main__":
    main()
