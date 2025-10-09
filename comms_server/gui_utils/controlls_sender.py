import json, socket, time, threading, pygame

def dz(x, dead):  # same as ps4_sender
    return 0.0 if abs(x) < dead else x

def start_controller_thread(
    pi_host: str,
    pi_port: int,
    on_state=None,             # optional callback: on_state(L, R, fwd, turn, raw)
    send_hz: float = 20.0,     # matches ps4_sender SEND_HZ
    deadzone: float = 0.10,    # matches ps4_sender DEAD
    max_speed: int = 100,      # matches ps4_sender MAXSPD
    fwd_axis: int = 1,         # SAME mapping as old code
    turn_axis: int = 2,        # SAME mapping as old code
    invert_fwd: bool = True,   # old code inverted Y (up = negative)
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
                # exactly like ps4_sender: pump events to refresh axes
                for _ in pygame.event.get():
                    pass

                # SAME axis math as ps4_sender
                fwd  = -dz(js.get_axis(fwd_axis), deadzone) if invert_fwd else dz(js.get_axis(fwd_axis), deadzone)
                turn =  dz(js.get_axis(turn_axis), deadzone)

                pan_axis: int = 3,      # example: right stick X
                tilt_axis: int = 4,     # example: right stick Y
                servo_range: int = 180, # degrees

                # differential drive + normalize (same as ps4_sender)
                Lf = fwd - turn
                Rf = fwd + turn
                m = max(1.0, abs(Lf), abs(Rf))
                L = int(max_speed * Lf / m)
                R = int(max_speed * Rf / m)
                # Servo controls (example mapping)

                pan = js.get_axis(pan_axis)
                tilt = js.get_axis(tilt_axis)
                # Convert -1..+1 -> 0..servo_range
                pan_deg  = int((pan + 1) * 0.5 * servo_range)
                tilt_deg = int((1 - tilt) * 0.5 * servo_range)

                now = time.time()
                if now - last >= period:
                    payload = json.dumps({
                        "L": L,
                        "R": R,
                        "servo_pan": pan_deg,
                        "servo_tilt": tilt_deg
                    }).encode("utf-8")

                    try:
                        sock.sendto(payload, target)
                        if debug:
                            print(f"[controller] SEND -> {payload!r}")
                    except Exception as e:
                        print(f"[controller] send error: {e!r}")
                    last = now

                if on_state:
                    try:
                        on_state(L, R, fwd, turn, {"raw_fwd": js.get_axis(fwd_axis), "raw_turn": js.get_axis(turn_axis)})
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
