import json, socket, time, pygame, math

PI_IP   = "192.168.137.184"
PI_PORT = 5005

SEND_HZ = 20.0
DEAD    = 0.1
MAXSPD  = 100

def dz(x, dead=DEAD):
    return 0 if abs(x) < dead else x

def main():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No joystick found."); return
    js = pygame.joystick.Joystick(0); js.init()
    print(f"Using: {js.get_name()}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    period = 1.0 / SEND_HZ
    last = 0.0

    try:
        while True:
            for event in pygame.event.get():
                pass

            # Axes
            fwd = -dz(js.get_axis(1))   # left stick Y
            turn =  dz(js.get_axis(2))  # right stick X
            L = fwd - turn
            R = fwd + turn
            m = max(1.0, abs(L), abs(R))
            L = int(MAXSPD * L / m)
            R = int(MAXSPD * R / m)

            # Buttons
            square   = js.get_button(0)
            cross    = js.get_button(1)
            circle   = js.get_button(2)
            triangle = js.get_button(3)

            now = time.time()
            if now - last >= period:
                msg = {
                    "L": L,
                    "R": R,
                    "square": square,
                    "circle": circle,
                    "triangle": triangle,
                    "cross": cross
                }
                print(msg)
                sock.sendto(json.dumps(msg).encode("utf-8"), (PI_IP, PI_PORT))
                last = now

            # Emergency stop still available
            if cross:  # X button
                sock.sendto(json.dumps({"stop":1}).encode("utf-8"), (PI_IP, PI_PORT))
                time.sleep(0.1)

            time.sleep(0.001)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()