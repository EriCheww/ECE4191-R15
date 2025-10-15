import customtkinter as ctk
import socket, json, threading

HEADER_COLUMNS  = [
    ( 1, None,  2, None),
    ( 3,  2,    4, None),
    ( 5,  3,    6, None),
    ( 7,  4,    8, 14),
    ( 9, None, 10, 15),
    (11, 17,   12, 18),
    (13, 27,   14, None),
    (15, 22,   16, 23),
    (17, None, 18, 24),
    (19, 10,   20, None),
    (21,  9,   22, 25),
    (23, 11,   24,  8),
    (25, None, 26,  7),
    (27,  0,   28,  1),
    (29,  5,   30, None),
    (31,  6,   32, 12),
    (33, 13,   34, None),
    (35, 19,   36, 16),
    (37, 26,   38, 20),
    (39, None, 40, 21),
]

GREEN = "#2ecc71"
YELLOW = "#f1c40f"
RED   = "#e74c3c"
GREY  = "#999999"
DARK  = "#333333"

LAMP_W = 20
LAMP_H = 20         
LAMP_RADIUS = 5

# Convenience for array-indexed updates (arr[0] is BCM 2, arr[25] is BCM 27)
GPIO_LAMPS_BY_BCM = {}
MOTOR_BCMS = (26, 21)


_last_conn_state = None
_last_motor_state = None

def _mk_lamp(parent, bcm):
    lamp = ctk.CTkLabel(
        parent, text="", width=LAMP_W, height=LAMP_H, corner_radius=LAMP_RADIUS,
        fg_color=(DARK if bcm is None else GREY)
    )
    if bcm is not None:
        GPIO_LAMPS_BY_BCM[bcm] = lamp
    return lamp


def create_gpio_panel(parent):
    """
    2 rows (row 0 = even pins, row 1 = odd pins), 20 columns left->right.
    Bottom-left is physical pin 1.
    Returns: (frame, lamps_by_bcm)
    """
    frame = ctk.CTkFrame(parent)
    small_font = ctk.CTkFont(size=10)

    for col, (odd_phys, odd_bcm, even_phys, even_bcm) in enumerate(HEADER_COLUMNS):
        inner  = ctk.CTkFrame(frame, fg_color="transparent")
        inner .grid(row=0, column=col, padx=2, pady=0, sticky="n")
        
        ctk.CTkLabel(inner , text=str(even_phys), font=small_font).grid(row=0, column=0, pady=0)
        _mk_lamp(inner , even_bcm).grid(row=1, column=0, pady=(0,4))
        _mk_lamp(inner , odd_bcm).grid(row=2, column=0, pady=0)
        ctk.CTkLabel(inner , text=str(odd_phys), font=small_font).grid(row=3, column=0, pady=0)


    # keep the panel from stretching
    frame.grid_rowconfigure(0, weight=0)
    frame.grid_rowconfigure(1, weight=0)
    for c in range(20):
        frame.grid_columnconfigure(c, weight=0)

    return frame, GPIO_LAMPS_BY_BCM


def update_gpio_colors(lamps_by_bcm, states):
    """
    states: dict { bcm_pin: 0|1 } – only BCMs present here will be colored.
    Others remain as-initialized (grey for power/GND or ID pins).
    """
    for bcm, lamp in lamps_by_bcm.items():
        if bcm not in states:
            continue  # leave non-reported pins grey
        val = 1 if states[bcm] else 0
        lamp.configure(fg_color=(GREEN if val else RED))


def create_simple_status(parent):

    frame = ctk.CTkFrame(parent)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)
    frame.grid_columnconfigure(2, weight=1)
    title = ctk.CTkLabel(frame, text="Status:", font=ctk.CTkFont(size=13, weight="bold"))
    title.grid(row=0, column=0, columnspan=3, sticky="n", padx=(10,10), pady=(10,0))

    label_connection_title = ctk.CTkLabel(frame, text="Connection")
    label_connection_title.grid(row=1, column=0, sticky="ew", padx=(10,0), pady=(10,0))
    lamp_connection = ctk.CTkLabel(frame, text="", width=LAMP_W, height=LAMP_H, corner_radius=LAMP_RADIUS, fg_color=RED)
    lamp_connection.grid(row=1, column=1, padx=(10,0), pady=(10,0))
    status_connection = ctk.CTkLabel(frame, text="Disconnected")
    status_connection.grid(row=1, column=2, sticky="ew", padx=(10,10), pady=(10,0))

    label_motor_title = ctk.CTkLabel(frame, text="Drive Motor")
    label_motor_title.grid(row=2, column=0, sticky="ew", padx=(10,0), pady=(10,0))
    lamp_motor = ctk.CTkLabel(frame, text="", width=LAMP_W, height=LAMP_H, corner_radius=LAMP_RADIUS, fg_color=YELLOW)
    lamp_motor.grid(row=2, column=1, padx=(10,0), pady=(10,0))
    status_motor = ctk.CTkLabel(frame, text="Idle")
    status_motor.grid(row=2, column=2, sticky="ew", padx=(10,10), pady=(10,0))

    return frame, lamp_connection, status_connection, lamp_motor, status_motor


def update_connection_status(pigpio_ok, lamp=None, label=None):
    """
    Updates the connection lamp and label based on pigpio_ok (True/False/None).
    - GREEN + "Connected" if True
    - RED   + "Disconnected" if False/None
    """
    global _last_conn_state
    ok = bool(pigpio_ok)

    color = GREEN if ok else RED
    text  = "Connected" if ok else "Disconnected"

    if lamp is not None:
        lamp.configure(fg_color=color)
    if label is not None and (_last_conn_state != ok):
        label.configure(text=text)

    _last_conn_state = ok


def update_motor_status(states, lamp=None, label=None):
    """
    Updates the motor lamp and label based on GPIO states.
    - Active = any monitored pin reads LOW (0)
    - Idle   = all monitored pins HIGH (1)
    """
    global _last_motor_state

    # Read pin levels; default to HIGH (inactive)
    levels = [states.get(b, 1) for b in MOTOR_BCMS]
    active = any(lv == 0 for lv in levels)  # LOW means active

    color = GREEN if active else YELLOW
    text  = "Active" if active else "Idle"

    if lamp is not None:
        lamp.configure(fg_color=color)
    if label is not None and (_last_motor_state != active):
        label.configure(text=text)

    _last_motor_state = active


def start_udp_listener(port, on_message):
    """
    Start a daemon thread that listens for UDP JSON messages:
      { "pi_connected": true/false, "gpio": {"2":{"level":0}, ...}}
    Calls on_message(arr, pigpio_ok, addr) on each valid packet.
    Returns a stop_event you can set() on shutdown.
    """
    stop_event = threading.Event()

    def run():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", port))
        s.settimeout(0.5)  # so we can check stop_event regularly
        print(f"Listening for Pi status on UDP {port}...")

        while not stop_event.is_set():
            try:
                data, addr = s.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break  # socket closed

            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue  # ignore malformed JSON

            pigpio_ok = msg.get("pi_connected")
            gpio = msg.get("gpio", {})
            arr = [1 if gpio.get(str(p), {}).get("level", 0) == 1 else 0
                   for p in range(2, 28)]
            try:
                on_message(arr, pigpio_ok, addr)
            except Exception:
                # Never let GUI exceptions kill the listener
                pass

        try:
            s.close()
        except Exception:
            pass

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return stop_event
