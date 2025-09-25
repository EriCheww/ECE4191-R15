import atexit
import customtkinter as ctk
import keyboard
import time
import re
from collections import deque
from tkwebview import TkWebview
from PIL import ImageGrab

from gui_utils.screenshot import take_screenshot
from gui_utils.console_window import init as console_init, open_console, add_to_console, clear_console, is_console_open
from gui_utils.settings_window import init as settings_init, open_settings, open_settings_page, is_settings_open, close_settings
from gui_utils.advanced_screenshot import advanced_screenshot_from_widget
from gui_utils.yolo_frame_detector import YOLOFrameDetector, RateLimiter
import gui_utils.app_settings as cfg     

##########################################################
# ---------------------- STYLE ---------------------------
##########################################################
HEADER_FONT = ("Arial", 14)
TRANSPARENT = "magenta"  

##########################################################
# ---------------- Global Variables ----------------------
##########################################################
console_win = None
console_text = None
yolo_toggle = False
_last_geo = None
_view_WH   = (1, 1)  
##########################################################
# ------------------- SETTINGS ---------------------------
##########################################################

# HOME_URL = "http://192.168.137.1:8080/"
HOME_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ/"

SS_SAVE_DIRECTORY = "C:\\ECE4191\\test_photos"
SS_USER_PREFIX = 'test'
YOLO_MODEL_PATH = r"C:\Users\Eric\Desktop\ECE4191\ECE4191-R15\comms_server\yolo\best.pt"

MAX_LOG_LINES = 2000  # keep last N lines; adjust as you like
LOG_BUFFER = deque(maxlen=MAX_LOG_LINES)



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
    else:
        yolo_toggle = True
        toggle_btn.configure(text="Stop Detection")
        # Ensure overlay is visible/topmost when starting
        overlay_win.deiconify()
        overlay_win.lift()
        root.after(1, yolo_detection)

def _widget_screen_bbox(w):
    w.update_idletasks()
    return (w.winfo_rootx(), w.winfo_rooty(), w.winfo_width(), w.winfo_height())

def _sync_overlay_to_web():
    global _last_geo, _view_WH
    if not root.winfo_exists(): return
    L, T, W, H = _widget_screen_bbox(web)   # LOGICAL coords/sizes
    geo = (L, T, W, H)
    if geo != _last_geo:
        overlay_win.geometry(f"{W}x{H}+{L}+{T}")  # geometry expects LOGICAL units
        _last_geo = geo
        _view_WH = (W, H)                         # <-- cache for drawing
    overlay_win.lift(root)
    root.after(66, _sync_overlay_to_web)

def enable_overlay_clickthrough():
    try:
        import ctypes
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_LAYERED = 0x00080000

        hwnd = overlay_win.winfo_id()
        user32 = ctypes.windll.user32
        get_window_long = user32.GetWindowLongW
        set_window_long = user32.SetWindowLongW

        exstyle = get_window_long(hwnd, GWL_EXSTYLE)
        exstyle |= (WS_EX_LAYERED | WS_EX_TRANSPARENT)
        set_window_long(hwnd, GWL_EXSTYLE, exstyle)
        add_to_console("Click Through Enabled")
    except Exception:
        add_to_console(f"Click Through Failed: {Exception}")

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


keyboard.on_press_key("w", lambda e: print_key("w"))
keyboard.on_press_key("a", lambda e: print_key("a"))
keyboard.on_press_key("s", lambda e: print_key("s"))
keyboard.on_press_key("d", lambda e: print_key("d"))
atexit.register(keyboard.unhook_all)



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
enable_overlay_clickthrough()

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
overlay_win.overrideredirect(True)      # no title bar
overlay_win.wm_attributes("-toolwindow", True)
overlay_win.transient(root)              
overlay_win.attributes("-topmost", False) 
overlay_win.configure(bg=TRANSPARENT)
# Windows color-key transparency:
overlay_win.wm_attributes("-transparentcolor", TRANSPARENT)

overlay = ctk.CTkCanvas(overlay_win, highlightthickness=0, bd=0, bg=TRANSPARENT)
overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

detector = YOLOFrameDetector(model_path=YOLO_MODEL_PATH, conf=0.25, iou=0.45)
limiter = RateLimiter(fps=10)

status_frame = ctk.CTkFrame(root)
status_frame.grid(row=2, column=0, sticky="nsew", padx=(10,10), pady=(10,10))

screenshot_button = ctk.CTkButton(status_frame, text="Take Screenshot", command=on_take_screenshot)
screenshot_button.grid(row=0, column=0, sticky="nsew", padx=(10,0), pady=(0,10))

advanced_screenshot_button = ctk.CTkButton(status_frame, text="Take Advanced Screenshot", command=on_take_advanced_screenshot)
advanced_screenshot_button.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=(0,10))

toggle_btn = ctk.CTkButton(status_frame, text="Start Detection", command=toggle_yolo)
toggle_btn.grid(row=2, column=0, sticky="nsew", padx=(10,0), pady=(0,10)) 

root.after(200, _sync_overlay_to_web)
root.after(50, lambda: (add_to_console("Navigating…"), safe_navigate()))

def _on_close():
    try:
        keyboard.unhook_all()
    finally:
        root.destroy()

root.protocol("WM_DELETE_WINDOW", _on_close)
root.mainloop()
