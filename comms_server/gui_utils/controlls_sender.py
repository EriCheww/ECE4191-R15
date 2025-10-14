import json, socket, time, threading, pygame

def dz(x, dead):
    x = float(x)
    return 0.0 if abs(x) < dead else x

def start_controller_thread(
    pi_host: str,
    pi_port: int,
    on_state=None,             # optional callback: on_state(L, R, fwd, turn, raw)
    send_hz: float = 20.0,     # matches ps4_sender SEND_HZ
    deadzone: float = 0.10,    # matches ps4_sender DEAD
    max_speed: int = 100,      # matches ps4_sender MAXSPD
    fwd_axis: int = 1,         # left stick Y
    turn_axis: int = 2,        # right stick X
    invert_fwd: bool = True,   # Y up is negative on many controllers
    # PS4 default button indices (DS4 over pygame):
    square_btn: int = 2,
    cross_btn: int = 0,
    circle_btn: int = 1,
    triangle_btn: int = 3,
    # Servo stepping (mirror receiver)
    MIN_DEG: int = 0,
    MAX_DEG: int = 180,
    STEP_DEG: int = 5,
    debug: bool = False,
):
    stop = threading.Event()

    def clamp(v, lo, hi):
        return lo if v < lo else hi if v > hi else v

    def run():
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            print("[controller] No joystick found."); return
        js = pygame.joystick.Joystick(0); js.init()
        print(f"[controller] Using: {js.get_name()} (axes={js.get_numaxes()} buttons={js.get_numbuttons()})")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        target = (pi_host, pi_port)
        period = 1.0 / max(1e-6, send_hz)
        last = 0.0

        # GUI-side mirror of receiver’s servo angles
        sg90_gui = 90  # Square/Circle servo
        mg90_gui = 90  # Triangle/Cross servo

        try:
            while not stop.is_set():
                # Pump events so pygame updates axis/button states
                for _ in pygame.event.get():
                    pass

                # Differential drive (L/R) from sticks
                fwd_raw  = js.get_axis(fwd_axis)
                turn_raw = js.get_axis(turn_axis)
                fwd  = -dz(fwd_raw, deadzone) if invert_fwd else dz(fwd_raw, deadzone)
                turn =  dz(turn_raw, deadzone)

                Lf = fwd - turn
                Rf = fwd + turn
                m = max(1.0, abs(Lf), abs(Rf))
                L = int(max_speed * Lf / m)
                R = int(max_speed * Rf / m)

                # Buttons (booleans 0/1) — same indices as receiver uses
                up = int(js.get_button(triangle_btn))
                down = int(js.get_button(cross_btn))
                left = int(js.get_button(square_btn))
                right = int(js.get_button(circle_btn))

                # --- GUI servo stepping (mirror receiver, step every tick while held) ---
                if up:    # SG90 decrease
                    sg90_gui = clamp(sg90_gui - STEP_DEG, MIN_DEG, MAX_DEG)
                if down:    # SG90 increase
                    sg90_gui = clamp(sg90_gui + STEP_DEG, MIN_DEG, MAX_DEG)
                if left:  # MG90 increase
                    mg90_gui = clamp(mg90_gui + STEP_DEG, MIN_DEG, MAX_DEG)
                if right:     # MG90 decrease
                    mg90_gui = clamp(mg90_gui - STEP_DEG, MIN_DEG, MAX_DEG)

                # Send to Pi: ONLY what the receiver uses (L/R + buttons)
                now = time.time()
                if now - last >= period:
                    payload_obj = {
                        "L": L,
                        "R": R,
                        "up": up,
                        "down": down,
                        "left": left,
                        "right": right,
                    }
                    print(payload_obj)
                    payload = json.dumps(payload_obj).encode("utf-8")
                    try:
                        sock.sendto(payload, target)
                        if debug:
                            print(f"[controller] {payload_obj}  | GUI sg90={sg90_gui} mg90={mg90_gui}")
                    except Exception as e:
                        print(f"[controller] send error: {e!r}")
                    last = now

                # Notify GUI with mirrored angles (pan=SG90, tilt=MG90)
                if on_state:
                    try:
                        on_state(L, R, fwd, turn, {
                            "raw_fwd": fwd_raw,
                            "raw_turn": turn_raw,
                            "pan_deg": sg90_gui,
                            "tilt_deg": mg90_gui,
                            "up":   up,       # NEW
                            "down": down,     # NEW
                            "left": left,     # NEW
                            "right": right,   # NEW
                        })
                    except Exception:
                        pass

                time.sleep(0.001)
        finally:
            try: sock.close()
            except: pass
            try: js.quit()
            except: pass
            try:
                pygame.joystick.quit()
                pygame.quit()
            except: pass

    threading.Thread(target=run, daemon=True).start()
    return stop
