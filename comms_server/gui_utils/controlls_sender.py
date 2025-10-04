# controller.py
import os, time, json, socket, threading, pygame

# Make pygame run headless (no window)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

def _deadzone(x, dz):
    return 0.0 if abs(x) < dz else x

def start_controller_thread(
    pi_host: str,
    pi_port: int,
    on_state=None,           # callback: on_state(L, R, fwd, turn, raw)
    send_hz: float = 20.0,
    deadzone: float = 0.10,
    max_speed: int = 100,
    fwd_axis: int = 1,       # left stick Y on most pads
    turn_axis: int = 2,      # right stick X on many PS controllers (sometimes 3)
    invert_fwd: bool = True, # stick up = positive forward
):
    """
    Starts a background thread that:
      - reads the first available gamepad via pygame
      - computes differential drive (L/R) from (fwd, turn)
      - sends {"L":..,"R":..} to (pi_host, pi_port) via UDP @ send_hz
      - calls on_state(L,R,fwd,turn, raw) for GUI display (if provided)
    Returns: stop_event (call .set() to stop the thread)
    """
    stop = threading.Event()

    def run():
        pygame.init()
        pygame.joystick.init()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        target = (pi_host, pi_port)
        period = 1.0 / max(1e-6, send_hz)
        last_sent = 0.0
        js = None

        try:
            # Find/attach joystick (retry until one appears or stopped)
            while not stop.is_set() and js is None:
                if pygame.joystick.get_count() > 0:
                    js = pygame.joystick.Joystick(0)
                    js.init()
                else:
                    time.sleep(0.25)
                    pygame.joystick.quit(); pygame.joystick.init()

            while not stop.is_set() and js is not None:
                # Pump events so axes update
                pygame.event.pump()

                # Read axes
                try:
                    raw_fwd = js.get_axis(fwd_axis)
                except Exception:
                    raw_fwd = 0.0
                try:
                    raw_turn = js.get_axis(turn_axis)
                except Exception:
                    raw_turn = 0.0

                fwd = _deadzone(-raw_fwd if invert_fwd else raw_fwd, deadzone)
                turn = _deadzone(raw_turn, deadzone)

                # Differential drive
                l_f = fwd - turn
                r_f = fwd + turn
                m = max(1.0, abs(l_f), abs(r_f))
                L = int(max_speed * l_f / m)
                R = int(max_speed * r_f / m)

                now = time.time()
                if now - last_sent >= period:
                    # Send UDP to Pi
                    try:
                        payload = json.dumps({"L": L, "R": R}).encode("utf-8")
                        sock.sendto(payload, target)
                    except Exception:
                        pass
                    last_sent = now

                # Notify GUI (caller must marshal to main thread if needed)
                if on_state:
                    try:
                        on_state(L, R, fwd, turn, {"raw_fwd": raw_fwd, "raw_turn": raw_turn})
                    except Exception:
                        pass

                time.sleep(0.002)
        finally:
            try: sock.close()
            except: pass
            try:
                if js: js.quit()
            except: pass
            try:
                pygame.joystick.quit()
                pygame.quit()
            except: pass

    threading.Thread(target=run, daemon=True).start()
    return stop
