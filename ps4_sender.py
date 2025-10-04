import json, socket, time, pygame, math

PI_IP   = "192.168.137.93"   # e.g. "192.168.1.50"
PI_PORT = 5005

# mapping and limits
SEND_HZ = 20.0
DEAD    = 0.1     # stick deadzone
MAXSPD  = 100     # percent

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
            # Pump events so pygame updates axes
            for event in pygame.event.get():
                pass

            # Typical DS4: left stick (axes 0=x, 1=y), right stick (2=x, 5/3=y)
            fwd = -dz(js.get_axis(1))  # up is negative; invert
            turn =  dz(js.get_axis(2)) # right stick X (some mappings use axis 3)

            # convert to differential drive
            L = fwd - turn
            R = fwd + turn
            # normalize if needed
            m = max(1.0, abs(L), abs(R))
            L = int(MAXSPD * L / m)
            R = int(MAXSPD * R / m)

            now = time.time()
            if now - last >= period:
                msg = json.dumps({"L": L, "R": R}).encode("utf-8")
                sock.sendto(msg, (PI_IP, PI_PORT))
                last = now

            # emergency stop with CROSS (X) button (DS4: button 0 or 1 depending on OS)
            # Print once to learn mapping:
            # print([js.get_button(i) for i in range(js.get_numbuttons())])
            if js.get_button(1):  # adjust index if needed
                sock.sendto(json.dumps({"stop":1}).encode("utf-8"), (PI_IP, PI_PORT))
                time.sleep(0.1)

            time.sleep(0.001)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
