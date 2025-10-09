import json, socket, time, threading, pygame

def dz(x, dead):
    x = float(x)
    return 0.0 if abs(x) < dead else x

def _read_axis(js, which):
    """Accepts an int index or a list/tuple of indices. Returns a single float in [-1.0, +1.0]."""
    if isinstance(which, (list, tuple)):
        vals = []
        for idx in which:
            try:
                vals.append(float(js.get_axis(int(idx))))
            except Exception:
                pass
        return sum(vals) / len(vals) if vals else 0.0
    return float(js.get_axis(int(which)))

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
    pan_axis: int = 3,         # right stick X for servo pan (adjust if needed)
    tilt_axis: int = 4,        # right stick Y for servo tilt (adjust if needed)
    servo_range: int = 180,    # degrees
    # PS4 default button indices (DS4 over pygame):
    square_btn: int = 0,
    cross_btn: int = 1,
    circle_btn: int = 2,
    triangle_btn: int = 3,
    debug: bool = False,
):
    stop = threading.Event()

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

        try:
            while not stop.is_set():
                # Pump events so pygame updates axis/button states
                for _ in pygame.event.get():
                    pass

                # Differential drive (L/R)
                fwd  = -dz(js.get_axis(fwd_axis), deadzone) if invert_fwd else dz(js.get_axis(fwd_axis), deadzone)
                turn =  dz(js.get_axis(turn_axis), deadzone)
                Lf = fwd - turn
                Rf = fwd + turn
                m = max(1.0, abs(Lf), abs(Rf))
                L = int(max_speed * Lf / m)
                R = int(max_speed * Rf / m)

                # Servo analog (absolute) angles from sticks
                pan  = _read_axis(js, pan_axis)
                tilt = _read_axis(js, tilt_axis)
                pan_deg  = int((pan + 1.0) * 0.5 * servo_range)      # map [-1,+1] → [0,180]
                tilt_deg = int((1.0 - tilt) * 0.5 * servo_range)     # invert Y

                # PS4 buttons (booleans 0/1)
                square   = int(js.get_button(square_btn))
                cross    = int(js.get_button(cross_btn))
                circle   = int(js.get_button(circle_btn))
                triangle = int(js.get_button(triangle_btn))

                now = time.time()
                if now - last >= period:
                    payload_obj = {
                        "L": L,
                        "R": R,
                        "servo_pan": pan_deg,
                        "servo_tilt": tilt_deg,
                        # include buttons so receiver can step servos
                        "square": square,
                        "cross": cross,
                        "circle": circle,
                        "triangle": triangle,
                    }
                    payload = json.dumps(payload_obj).encode("utf-8")

                    try:
                        sock.sendto(payload, target)
                        if debug:
                            print(f"[controller] {payload_obj}")
                    except Exception as e:
                        print(f"[controller] send error: {e!r}")
                    last = now

                if on_state:
                    try:
                        on_state(L, R, fwd, turn, {
                            "raw_fwd": js.get_axis(fwd_axis),
                            "raw_turn": js.get_axis(turn_axis)
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
