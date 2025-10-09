import customtkinter as ctk
import time
import re
from collections import deque
from tkwebview import TkWebview
from PIL import ImageGrab

from gui_utils.screenshot import take_screenshot
from gui_utils.console_window import init as console_init, open_console, add_to_console
from gui_utils.settings_window import init as settings_init, open_settings
from gui_utils.advanced_screenshot import advanced_screenshot_from_widget
from gui_utils.yolo_frame_detector import YOLOFrameDetector, RateLimiter
from gui_utils.alert import show_alert
from gui_utils.status import *
from gui_utils.controlls_sender import start_controller_thread

import gui_utils.app_settings as cfg     

##########################################################
# ---------------------- STYLE ---------------------------
##########################################################
HEADER_FONT = ("Arial", 14)
TRANSPARENT = "magenta"  

GREEN = "#2ecc71"
RED   = "#e74c3c"

##########################################################
# ---------------- Global Variables ----------------------
##########################################################
console_win = None
console_text = None
yolo_toggle = False
_last_geo = None
_view_WH   = (1, 1)  

GPIO_LAMPS = {} 
STOP_EVENT = None
##########################################################
# ------------------- SETTINGS ---------------------------
##########################################################

HOME_URL = "http://192.168.137.1:8080/"
# HOME_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ/"

SS_SAVE_DIRECTORY = "C:\\ECE4191\\test_photos"
SS_USER_PREFIX = 'test'
YOLO_MODEL_PATH = r"C:\Users\ericl\OneDrive\Documents\GitHub\ECE4191-R15\comms_server\yolo\best.pt"

YOLO_FPS_LIMITER = 10

MAX_LOG_LINES = 2000  # keep last N lines; adjust as you like
LOG_BUFFER = deque(maxlen=MAX_LOG_LINES)

STATUS_PORT = 5051
PINS = list(range(2,28))

PI_IP   = "192.168.137.144" 
PI_PORT = 5005

##########################################################
# ------------------ FUNCTIONS ---------------------------
##########################################################

def print_key(ch: str):
    print(ch, flush=True)

def fresh_url(url: str) -> str:
    sep = '&' if '?' in url else '?'
    return f"{url}{sep}cb={int(time.time())}"

def safe_navigate():
    try:
        web.navigate(fresh_url(HOME_URL))
        add_to_console("Connecting to stream...")
    except Exception as e:
        add_to_console("Error Loading URL")

def on_take_screenshot():
    save_dir = cfg.settings.get("ss_save_directory")
    prefix   = cfg.settings.get("ss_user_prefix")
    success, result = take_screenshot(web, save_dir, prefix)
    if success:
        add_to_console(f"Screenshot saved: {result}")
        show_alert(root, f"Screenshot saved: {result}", "Success!")
    else:
        add_to_console(f"Failed: {result}")

def on_take_advanced_screenshot():
    """Capture the web area and open the annotation window."""
    try:
        target_widget = web_frame  
        ok, info = advanced_screenshot_from_widget(target_widget)

        add_to_console(f"Annotation {'saved:' if ok else 'canceled:'} {info}")
    except Exception as e:
        add_to_console(f"Annotation failed: {e!r}")

def sanitize_prefix(s: str) -> str:
    # Remove illegal filename chars and trim spaces
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", s).strip()

def yolo_detection():
    if not yolo_toggle or not root.winfo_exists():
        return
    try:
        if not limiter.ok():
            return

        # 1) Live bbox of the web frame (logical coords)
        bbox, _ = target_bbox_px()
        L, T, R, B = bbox
        ow, oh = (R - L), (B - T)

        # 2) Try a logical-coords grab first
        test_img = ImageGrab.grab(bbox=(L, T, R, B))

        # If PIL returned the expected logical size, use it.
        # Otherwise, fall back to a DPR-scaled (physical) grab.
        if test_img.size == (ow, oh):
            frame_img = test_img
        else:
            dpr = _dpi_scale_for_window(web.winfo_id())
            phys_bbox = (int(L*dpr), int(T*dpr), int(R*dpr), int(B*dpr))
            frame_img = ImageGrab.grab(bbox=phys_bbox)

        # 3) Detect normalized to the grabbed image itself
        dets = detector.detect_image(frame_img)

        # 4) Hard-sync overlay geometry to the bbox for THIS frame
        overlay_win.geometry(f"{ow}x{oh}+{L}+{T}")
        overlay.config(width=ow, height=oh)
        overlay.delete("all")

        # Optional always-visible border to verify alignment
        overlay.create_rectangle(1, 1, ow-2, oh-2, outline="lime")

        # 5) Draw using the live ow/oh (not a cached _view_WH)
        for d in dets:
            x1 = int(d.x1n * ow); y1 = int(d.y1n * oh)
            x2 = int(d.x2n * ow); y2 = int(d.y2n * oh)
            overlay.create_rectangle(x1, y1, x2, y2, width=2, outline="yellow")
            overlay.create_text(x1+4, y1+12, anchor="w",
                                text=f"{d.label} {d.conf:.2f}", fill="white")
            
    finally:
        if yolo_toggle and root.winfo_exists():
            root.after(100, yolo_detection)

def toggle_yolo():
    """Start/stop YOLO detection + overlay drawing."""
    global yolo_toggle
    if yolo_toggle:
        yolo_toggle = False
        toggle_btn.configure(text="Start Detection")
        overlay.delete("all")
        # drop topmost when stopping (optional)
        overlay_win.attributes("-topmost", False)
    else:
        yolo_toggle = True
        toggle_btn.configure(text="Stop Detection")
        overlay_win.deiconify()
        # CRUCIAL: keep overlay above the WebView HWND
        overlay_win.attributes("-topmost", True)
        overlay_win.lift()
        root.after(1, yolo_detection)

def _widget_screen_bbox(w):
    w.update_idletasks()
    return (w.winfo_rootx(), w.winfo_rooty(), w.winfo_width(), w.winfo_height())

def _sync_overlay_to_web():
    global _last_geo, _view_WH
    if not root.winfo_exists(): return
    L, T, W, H = _widget_screen_bbox(web)
    geo = (L, T, W, H)
    if geo != _last_geo:
        overlay_win.geometry(f"{W}x{H}+{L}+{T}")
        _last_geo = geo
        _view_WH = (W, H)
    # keep it above everything (important for WebView)
    overlay_win.lift()              # <-- remove the (root) argument
    root.after(10, _sync_overlay_to_web)

def target_bbox_px():
    """Screen coords (left, top, right, bottom) of the *exact* widget we target."""
    web.update_idletasks()
    L = web.winfo_rootx()
    T = web.winfo_rooty()
    W = web.winfo_width()
    H = web.winfo_height()
    return (L, T, L + W, T + H), (W, H)

def _dpi_scale_for_window(hwnd: int) -> float:
    try:
        import ctypes
        MONITOR_DEFAULTTONEAREST = 2
        user32 = ctypes.windll.user32
        shcore = ctypes.windll.shcore
        monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        dpiX = ctypes.c_uint()
        dpiY = ctypes.c_uint()
        # GetDpiForMonitor returns DPI (96 == 100%)
        shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(dpiX), ctypes.byref(dpiY))
        return dpiX.value / 96.0
    except Exception:
        return 1.0


# === ADD: UDP listener callback ===
def _on_udp_message(arr, pigpio_ok, addr):
    # Called from the background thread — hop to GUI thread:
    root.after(0, _apply_gpio_update, arr, pigpio_ok, addr)

def _apply_gpio_update(arr, pigpio_ok, addr):
    try:
        add_to_console(f"UDP {addr[0]} pigpio={'OK' if pigpio_ok else 'DISCONNECTED'}")
    except Exception:
        pass

    # Convert 26-length array (BCM 2..27) to dict {bcm:0|1}
    states = {bcm: arr[bcm - 2] for bcm in range(2, 28) if 0 <= (bcm - 2) < len(arr)}

    # Update individual GPIO lamps
    update_gpio_colors(LAMPS, states)

    # Update the Motor Status lamp
    update_connection_status(pigpio_ok, lamp=lamp_conn, label=label_conn)
    update_motor_status(states, lamp=lamp_motor, label=label_motor)



##########################################################
# --------------------- GUI ------------------------------
##########################################################

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title("Viewer")
root.geometry("1180x740")
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=110)
root.grid_rowconfigure(2, weight=30)
root.grid_columnconfigure(0, weight=1)

SS_SAVE_DIRECTORY_VAR   = ctk.StringVar(value=SS_SAVE_DIRECTORY)
SS_USER_PREFIX_VAR = ctk.StringVar(value=SS_USER_PREFIX)

# Initialize the console manager
add_to_console("App starting…")

try:
    console_init(root, max_lines=2000, auto_open=False)
    add_to_console(f"Console init OK")
except Exception as e:
    add_to_console(f"Console init FAILED: {e!r}")

# Settings init
try:
    settings_init(root)
    add_to_console("Settings init OK")
except Exception as e:
    add_to_console(f"Settings init FAILED: {e!r}")

top_bar_frame = ctk.CTkFrame(root, fg_color="transparent")
top_bar_frame.grid(row=0, column=0, sticky="nsew", padx=(10,10), pady=(10,0))
top_bar_frame.grid_rowconfigure(0, weight=1)
# top_bar_frame.grid_columnconfigure(0, weight=1)

console_button = ctk.CTkButton(top_bar_frame, text="Console", command=open_console)
console_button. grid(row=0, column=0, sticky="nsew", padx=(0,0), pady=(0,0)) 

settings_button = ctk.CTkButton(top_bar_frame, text="Settings", command=open_settings)
settings_button. grid(row=0, column=1, sticky="nsew", padx=(10,10), pady=(0,0)) 

help_button = ctk.CTkButton(top_bar_frame, text="Help")
help_button. grid(row=0, column=2, sticky="nsew", padx=(0,0), pady=(0,0)) 

# Web browser container
web_frame = ctk.CTkFrame(root)
web_frame.grid(row=1, column=0, sticky="nsew", padx=(10,10), pady=(10,0))

try:
    web = TkWebview(web_frame)
    web.pack(fill="both", expand=True)
    add_to_console("WebView created OK")
except Exception as e:
    add_to_console(f"WebView init failed: {e}")

overlay_win = ctk.CTkToplevel(root)
overlay_win.overrideredirect(True)
overlay_win.wm_attributes("-toolwindow", True)
overlay_win.transient(root)              
overlay_win.attributes("-topmost", False) 
overlay_win.configure(bg=TRANSPARENT)
overlay_win.wm_attributes("-transparentcolor", TRANSPARENT)

overlay = ctk.CTkCanvas(overlay_win, highlightthickness=0, bd=0, bg=TRANSPARENT)
overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

detector = YOLOFrameDetector(model_path=YOLO_MODEL_PATH, conf=0.25, iou=0.45)
limiter = RateLimiter(fps=YOLO_FPS_LIMITER) 

status_frame = ctk.CTkFrame(root)
status_frame.grid(row=2, column=0, sticky="nsew", padx=(10,10), pady=(10,10))
status_frame.grid_columnconfigure(1, weight=0)

screenshot_button = ctk.CTkButton(status_frame, text="Take Screenshot", command=on_take_screenshot)
screenshot_button.grid(row=0, column=0, sticky="nsew", padx=(10,0), pady=(0,10))

advanced_screenshot_button = ctk.CTkButton(status_frame, text="Take Advanced Screenshot", command=on_take_advanced_screenshot)
advanced_screenshot_button.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=(0,10))

toggle_btn = ctk.CTkButton(status_frame, text="Start Detection", command=toggle_yolo)
toggle_btn.grid(row=2, column=0, sticky="nsew", padx=(10,0), pady=(0,10)) 

gpio_frame, LAMPS = create_gpio_panel(status_frame)
gpio_frame.grid(row=0, column=1, sticky="n", padx=(10,0), pady=(0,10))

# from gui_utils.status import create_simple_status, update_simple_status, update_connection_status
simple_status_frame, lamp_conn, label_conn, lamp_motor, label_motor = create_simple_status(parent=status_frame)
simple_status_frame.grid(row=0, column=3, sticky="n", padx=(10,0), pady=(0,10))

STOP_EVENT = start_udp_listener(STATUS_PORT, _on_udp_message)

controller_frame = ctk.CTkFrame(status_frame)
controller_frame.grid(row=0, column=2, rowspan=3, sticky="n", padx=(10,10), pady=(0,10))
controller_frame.grid_columnconfigure(1, weight=1)

controller_frame_label = ctk.CTkLabel(controller_frame, text="Controller")
controller_frame_label.grid(row=0, column=0, columnspan=2, pady=(0,6))

# Vars for text readouts
fwd_var  = ctk.StringVar(value="Fwd: 0.00")
turn_var = ctk.StringVar(value="Turn: 0.00")

# --- Vertical Fwd/Back (orientation='vertical') ---
ct_fwd_label = ctk.CTkLabel(controller_frame, textvariable=fwd_var)
ct_fwd_label.grid(row=1, column=0, sticky="w")
ct_fwd = ctk.CTkProgressBar(controller_frame, orientation="vertical", width=14, height=90)
ct_fwd.grid(row=2, column=0, sticky="ns", padx=(0,8))
ct_fwd.set(0.5) 

# --- Horizontal Left/Right ---
ct_turn_label = ctk.CTkLabel(controller_frame, textvariable=turn_var).grid(row=1, column=1, sticky="w")
ct_turn = ctk.CTkProgressBar(controller_frame)
ct_turn.grid(row=2, column=1, sticky="ew")
ct_turn.set(0.5)  # 0.5 = neutral

# Make the right column stretch so the horizontal bar can expand nicely


def _on_controller_state(L, R, fwd, turn, raw):
    """
    Runs on controller thread; hop to GUI thread.
    Expecting fwd, turn in [-1.0, +1.0].
    """
    # Map [-1,+1] -> [0,1] where 0.5 is neutral
    fwd_val  = (float(fwd) + 1.0) / 2.0
    turn_val = (float(turn) + 1.0) / 2.0

    # Clamp just in case
    fwd_val  = 0.0 if fwd_val  < 0.0 else 1.0 if fwd_val  > 1.0 else fwd_val
    turn_val = 0.0 if turn_val < 0.0 else 1.0 if turn_val > 1.0 else turn_val

    root.after(0, lambda: (
        ct_fwd.set(fwd_val),
        ct_turn.set(turn_val),
        fwd_var.set(f"Fwd: {fwd:+.2f}"),
        turn_var.set(f"Turn: {turn:+.2f}")
    ))

# Keep your existing controller thread start; on_state already passes (L, R, fwd, turn, raw)
CONTROLLER_STOP = start_controller_thread(
    PI_IP, PI_PORT,
    on_state=_on_controller_state,
    send_hz=20.0, deadzone=0.10, max_speed=100,
    fwd_axis=1, turn_axis=2, invert_fwd=True, debug=False
)
root.after(200, _sync_overlay_to_web)
root.after(50, lambda: (add_to_console("Navigating…"), safe_navigate()))

def _on_close():
    try:
        if STOP_EVENT:
            STOP_EVENT.set()
        if CONTROLLER_STOP:
            CONTROLLER_STOP.set()

    finally:
        root.destroy()

root.protocol("WM_DELETE_WINDOW", _on_close)
root.mainloop()
