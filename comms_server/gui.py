import customtkinter as ctk
import time
import re
from collections import deque
from tkwebview import TkWebview
from PIL import ImageGrab
from typing import List

from gui_utils.screenshot import take_screenshot
from gui_utils.console_window import init as console_init, open_console, add_to_console, dock_console
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
# HOME_URL = "https://www.google.com/search?sca_esv=44ea4fb9ad3aef3e&rlz=1C1ONGR_en-GBAU994AU994&sxsrf=AE3TifN1zh2j7D6LCpFWQvvK1aRohfxavg:1760049280810&udm=2&fbs=AIIjpHxU7SXXniUZfeShr2fp4giZ1Y6MJ25_tmWITc7uy4KIeoJTKjrFjVxydQWqI2NcOhYPURIv2wPgv_w_sE_0Sc6QJ-Br1HsjcCS2iult3qabYNSTRQw7e6gotLtdd5x8UIIgeCE6NBgQsSbPuekL9rjVZJWQEAHj1U8xULGicvCjCVz7e4mx-Cn5e84mUA7j5VECxV62zqnn0Se2QWy97yLZg6wjTg&q=kangaroo&sa=X&ved=2ahUKEwjX3K3BlpiQAxVT4zgGHYGkHfIQtKgLegQIFxAB&biw=1664&bih=983&dpr=1.5#vhid=pmU6Z0ZOXIKHzM&vssid=mosaic"

SS_SAVE_DIRECTORY = "C:\\ECE4191\\test_photos"
SS_USER_PREFIX = 'test'
YOLO_MODEL_PATH = r"C:\Users\Eric\Desktop\ECE4191\ECE4191-R15\comms_server\yolo\best_v3.pt"

YOLO_FPS_LIMITER = 10

MAX_LOG_LINES = 2000  # keep last N lines; adjust as you like
LOG_BUFFER = deque(maxlen=MAX_LOG_LINES)

STATUS_PORT = 5051
PINS = list(range(2,28))

PI_IP   = "192.168.137.94" 
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

# YOLO Detection 
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

        # 2) Grab the frame (logical first, then HiDPI fallback)
        test_img = ImageGrab.grab(bbox=(L, T, R, B))
        if test_img.size == (ow, oh):
            frame_img = test_img
        else:
            dpr = _dpi_scale_for_window(web.winfo_id())
            phys_bbox = (int(L*dpr), int(T*dpr), int(R*dpr), int(B*dpr))
            frame_img = ImageGrab.grab(bbox=phys_bbox)

        # 3) Run detection
        dets = detector.detect_image(frame_img)

        # 4) Confidence pruning (optional)
        MIN_CONF = 0.25
        dets = [d for d in dets if d.conf >= MIN_CONF]

        # 5) Class-agnostic NMS (keep highest-conf per overlap)
        def _iou_xyxy(a, b) -> float:
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            ix1, iy1 = max(ax1, bx1), max(ay1, by1)
            ix2, iy2 = min(ax2, bx2), min(ay2, by2)
            iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
            inter = iw * ih
            if inter == 0:
                return 0.0
            a_area = (ax2 - ax1) * (ay2 - ay1)
            b_area = (bx2 - bx1) * (by2 - by1)
            return inter / float(a_area + b_area - inter)

        def _greedy_nms(dets_list, iou_thr: float = 0.50):
            if not dets_list:
                return []
            dets_sorted = sorted(dets_list, key=lambda d: d.conf, reverse=True)
            keep = []
            for d in dets_sorted:
                bb = (d.x1, d.y1, d.x2, d.y2)
                if all(_iou_xyxy(bb, (k.x1, k.y1, k.x2, k.y2)) < iou_thr for k in keep):
                    keep.append(d)
            return keep

        IOU_THR = 0.50
        dets = _greedy_nms(dets, iou_thr=IOU_THR)

        # 6) Sync overlay to this frame and draw survivors
        overlay_win.geometry(f"{ow}x{oh}+{L}+{T}")
        overlay.config(width=ow, height=oh)
        overlay.delete("all")
        overlay.create_rectangle(1, 1, ow-2, oh-2, outline="lime")

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
    # update_gpio_colors(LAMPS, states)

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
root.grid_rowconfigure(2, weight=0)
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
status_frame.grid_rowconfigure(0, weight=1)
status_frame.grid_columnconfigure(0, weight=3)
status_frame.grid_columnconfigure(1, weight=3)
status_frame.grid_columnconfigure(2, weight=1)

buttons_frame = ctk.CTkFrame(status_frame)
buttons_frame.grid(row=0, column=3, sticky="nsew", padx=(10,0), pady=(10,10))
buttons_frame_label = ctk.CTkLabel(buttons_frame, text="Quick Actions:", font=ctk.CTkFont(size=13, weight="bold"))
buttons_frame_label.grid(row=0, column=0, sticky="nsew", padx=(10,10), pady=(10,10))

screenshot_button = ctk.CTkButton(buttons_frame, text="Take Screenshot", command=on_take_screenshot)
screenshot_button.grid(row=1, column=0, sticky="nsew", padx=(10,10), pady=(10,10))

advanced_screenshot_button = ctk.CTkButton(buttons_frame, text="Take Advanced Screenshot", command=on_take_advanced_screenshot)
advanced_screenshot_button.grid(row=2, column=0, sticky="nsew", padx=(10,10), pady=(0,10))

toggle_btn = ctk.CTkButton(buttons_frame, text="Start Detection", command=toggle_yolo)
toggle_btn.grid(row=3, column=0, sticky="nsew", padx=(10,10), pady=(0,10)) 

# gpio_frame, LAMPS = create_gpio_panel(status_frame)
# gpio_frame.grid(row=0, column=1, sticky="n", padx=(10,0), pady=(0,10))

# from gui_utils.status import create_simple_status, update_simple_status, update_connection_status
simple_status_frame, lamp_conn, label_conn, lamp_motor, label_motor = create_simple_status(parent=status_frame)
simple_status_frame.grid(row=0, column=2, sticky="nsew", padx=(0,0), pady=(10,10))

STOP_EVENT = start_udp_listener(STATUS_PORT, _on_udp_message)

controller_frame = ctk.CTkFrame(status_frame)
controller_frame.grid(row=0, column=0, sticky="nsew", padx=(10,10), pady=(10,10))
controller_frame.grid_rowconfigure(1, weight=1)
controller_frame.grid_rowconfigure(2, weight=1)
controller_frame.grid_columnconfigure(0, weight=1)
controller_frame.grid_columnconfigure(1, weight=2)

controller_frame_label = ctk.CTkLabel(controller_frame, text="Controller:", font=ctk.CTkFont(size=13, weight="bold"))
controller_frame_label.grid(row=0, column=0, columnspan=2, padx=(10,10), pady=(10,0))

# Vars for text readouts
fwd_var  = ctk.StringVar(value="Fwd: 0.00")
turn_var = ctk.StringVar(value="Turn: 0.00")

# --- Vertical Fwd/Back (orientation='vertical') ---
ct_fwd_label = ctk.CTkLabel(controller_frame, textvariable=fwd_var)
ct_fwd_label.grid(row=1, column=0, sticky="nsew")
ct_fwd = ctk.CTkProgressBar(controller_frame, orientation="vertical")
ct_fwd.grid(row=2, column=0, padx=(0,8), pady=(10,10))
ct_fwd.set(0.5) 

# --- Horizontal Left/Right ---
ct_turn_label = ctk.CTkLabel(controller_frame, textvariable=turn_var)
ct_turn_label.grid(row=1, column=1, sticky="nsew")
ct_turn = ctk.CTkProgressBar(controller_frame)
ct_turn.grid(row=2, column=1)
ct_turn.set(0.5)  # 0.5 = neutral

console_panel = console_panel = dock_console(status_frame,place=lambda f: f.grid(row=0, column=4, sticky="nsew",padx=(10,10), pady=(10,10)))


# ===================== Camera Angle Panel =====================
camera_frame = ctk.CTkFrame(status_frame)
camera_frame.grid(row=0, column=1, sticky="nsew", padx=(0,10), pady=(10,10))

# Grid: left column = aim (flex), right column = controls (fixed-ish)
camera_frame.grid_columnconfigure(0, weight=2)
camera_frame.grid_columnconfigure(1, weight=1)
# Rows: let row 0 stretch so the aim can grow; rows 1–3 are for right-side controls
camera_frame.grid_rowconfigure(0, weight=0)   # aim grows vertically
camera_frame.grid_rowconfigure(1, weight=0)
camera_frame.grid_rowconfigure(2, weight=0)
camera_frame.grid_rowconfigure(3, weight=0)

ct_cam_label = ctk.CTkLabel(camera_frame, text="Camera Angle:", font=ctk.CTkFont(size=13, weight="bold"))
ct_cam_label.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=(0,0), pady=(10,0))  # title above right stack

# ---------- Left: Aim canvas ----------
AIM_SIZE = 280  # fixed baseline size (won't force other frames to resize)
aim_wrap = ctk.CTkFrame(camera_frame, fg_color="transparent")
aim_wrap.grid(row=1, column=0, rowspan=3, sticky="nsew", padx=(0,0), pady=(10,10))
aim_wrap.grid_rowconfigure(0, weight=1)
aim_wrap.grid_columnconfigure(0, weight=1)

aim = ctk.CTkCanvas(aim_wrap, width=AIM_SIZE, height=AIM_SIZE, highlightthickness=0, bg="#111111")
aim.place(relx=0.5, rely=0.5, anchor="center")  # center within the left cell

# draw border + crosshair for the fixed baseline size
aim.create_rectangle(1, 1, AIM_SIZE-2, AIM_SIZE-2, outline="#555555")
aim.create_line(AIM_SIZE//2, 2, AIM_SIZE//2, AIM_SIZE-2, fill="#333333")
aim.create_line(2, AIM_SIZE//2, AIM_SIZE-2, AIM_SIZE//2, fill="#333333")

_marker_r = 5
marker_id = aim.create_oval(
    AIM_SIZE//2 - _marker_r, AIM_SIZE//2 - _marker_r,
    AIM_SIZE//2 + _marker_r, AIM_SIZE//2 + _marker_r,
    outline="", fill="#00e676"
)

# ---------- Right: stacked controls (Pan, Tilt, D-pad) ----------
# Pan/Tilt readouts (centered, fixed width so text changes don't jiggle layout)
LABEL_W = 120
pan_var  = ctk.StringVar(value="Pan: 90°")
tilt_var = ctk.StringVar(value="Tilt: 90°")

ct_pan_label  = ctk.CTkLabel(camera_frame, textvariable=pan_var, anchor="center", width=LABEL_W)
ct_pan_label.grid(row=1, column=1, sticky="n", pady=(6,2))

ct_tilt_label = ctk.CTkLabel(camera_frame, textvariable=tilt_var, anchor="center", width=LABEL_W)
ct_tilt_label.grid(row=2, column=1, sticky="n", pady=(2,8))

# D-Pad indicator
dpad = ctk.CTkCanvas(camera_frame, width=70, height=70, highlightthickness=0, bg="#111111")
dpad.grid(row=3, column=1, sticky="n")
_up    = dpad.create_polygon(35, 8, 25, 22, 45, 22,  fill="#333333", outline="")
_down  = dpad.create_polygon(35, 62, 25, 48, 45, 48, fill="#333333", outline="")
_left  = dpad.create_polygon(8, 35, 22, 25, 22, 45,  fill="#333333", outline="")
_right = dpad.create_polygon(62, 35, 48, 25, 48, 45, fill="#333333", outline="")

def _light(widget_id, on):
    dpad.itemconfig(widget_id, fill="#00e5ff" if on else "#333333")

# ---- Marker mapping (keeps your current inversion flags) ----
PAN_RIGHT_INCREASES = True
TILT_DOWN_INCREASES = True

def _clamp_deg(v: int) -> int:
    return max(0, min(180, int(v)))

def _move_marker(pan_deg: int, tilt_deg: int):
    pan  = _clamp_deg(pan_deg)
    tilt = _clamp_deg(tilt_deg)

    # X from tilt (reversed so right=right), Y from pan
    x = int((1.0 - (tilt / 180.0)) * (AIM_SIZE - 1))
    y = int((pan / 180.0) * (AIM_SIZE - 1))

    if not PAN_RIGHT_INCREASES:
        x = (AIM_SIZE - 1) - x
    if not TILT_DOWN_INCREASES:
        y = (AIM_SIZE - 1) - y

    aim.coords(marker_id, x - _marker_r, y - _marker_r, x + _marker_r, y + _marker_r)

# ---------- Update hook: extend your existing _on_controller_state ----------
def _on_controller_state(L, R, fwd, turn, raw):
    # existing bars
    fwd_val  = (float(fwd) + 1.0) / 2.0
    turn_val = (float(turn) + 1.0) / 2.0
    fwd_val  = 0.0 if fwd_val  < 0.0 else 1.0 if fwd_val  > 1.0 else fwd_val
    turn_val = 0.0 if turn_val < 0.0 else 1.0 if turn_val > 1.0 else turn_val

    # angles from sender (already stepped to match receiver)
    pan_deg  = int(raw.get("pan_deg", 90))
    tilt_deg = int(raw.get("tilt_deg", 90))

    # D-Pad states (require the tiny sender tweak above)
    up    = int(raw.get("up", 0))
    down  = int(raw.get("down", 0))
    left  = int(raw.get("left", 0))
    right = int(raw.get("right", 0))

    def _ui():
        # update your existing widgets
        ct_fwd.set(fwd_val)
        ct_turn.set(turn_val)
        fwd_var.set(f"Fwd: {fwd:+.2f}")
        turn_var.set(f"Turn: {turn:+.2f}")

        # update angle panel
        pan_var.set(f"Pan: {pan_deg:3d}°")
        tilt_var.set(f"Tilt: {tilt_deg:3d}°")
        _move_marker(pan_deg, tilt_deg)

        # light up D-Pad
        _light(_up,    up)
        _light(_down,  down)
        _light(_left,  left)
        _light(_right, right)

    root.after(0, _ui)

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
