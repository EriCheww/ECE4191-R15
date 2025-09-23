import atexit
import customtkinter as ctk
import keyboard
import time
import re
from collections import deque
from tkwebview import TkWebview

from gui_utils.screenshot import take_screenshot
from gui_utils.console_window import init as console_init, open_console, add_to_console, clear_console, is_console_open
from gui_utils.settings_window import init as settings_init, open_settings, open_settings_page, is_settings_open, close_settings
from gui_utils.advanced_screenshot import advanced_screenshot_from_widget
import gui_utils.app_settings as cfg    

import subprocess, sys, os, platform

##########################################################
# ---------------------- STYLE ---------------------------
##########################################################
HEADER_FONT = ("Arial", 14)

##########################################################
# ---------------- Global Variables ----------------------
##########################################################
console_win = None
console_text = None
det_proc = None  # detector subprocess handle
##########################################################
# ------------------- SETTINGS ---------------------------
##########################################################

HOME_URL = "http://192.168.137.1:8080/"
# HOME_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ/"

SS_SAVE_DIRECTORY = "C:\\ECE4191\\test_photos"
SS_USER_PREFIX = 'test'

MAX_LOG_LINES = 2000  # keep last N lines; adjust as you like
LOG_BUFFER = deque(maxlen=MAX_LOG_LINES)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(THIS_DIR, "best.pt")  # ensure correct path

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
        # Option A: let the helper read save_dir & prefix from your settings
        target_widget = web_frame  # or `web` if TkWebview is a real Tk widget
        ok, info = advanced_screenshot_from_widget(target_widget)

        # Option B (explicit): choose dir/prefix yourself
        # save_dir = cfg.settings.get("ss_save_directory") or fd.askdirectory(title="Pick save folder")
        # prefix   = cfg.settings.get("ss_user_prefix") or "user"
        # ok, info = take_advanced_screenshot(target_widget, save_dir, prefix)

        add_to_console(f"Annotation {'saved:' if ok else 'canceled:'} {info}")
    except Exception as e:
        add_to_console(f"Annotation failed: {e!r}")

def sanitize_prefix(s: str) -> str:
    # Remove illegal filename chars and trim spaces
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", s).strip()

def auto_detection():
    global det_proc
    if det_proc is None or det_proc.poll() is not None:
        # start
        python = sys.executable
        det_cmd = [
            sys.executable, os.path.join(THIS_DIR, "YOLO_overlay2.py"),
            "--port", "5600", "--pt", "96", "--clock-rate", "90000", "--latency-ms", "5",
            "--model", MODEL_PATH, "--conf", "0.25",
        ]

        det_proc = subprocess.Popen(det_cmd)
        auto_detection_button.configure(text="Stop Auto Detection")
        print("YOLO detector started on udp://127.0.0.1:5600")
    else:
        # stop
        det_proc.terminate()
        try: det_proc.wait(timeout=2)
        except: det_proc.kill()
        det_proc = None
        auto_detection_button.configure(text="Activate Auto Detection")
        print("YOLO detector stopped")


def start_detector():
    global det_proc
    if det_proc and det_proc.poll() is None:
        return
    py = sys.executable
    cmd = [py, "-u", "YOLO_overlay2.py", "--port", "5600", "--pt", "96",
           "--clock-rate", "90000", "--model", "best.pt", "--conf", "0.25"]
    creationflags = 0
    if platform.system() == "Windows":
        # CREATE_NO_WINDOW | DETACHED_PROCESS
        creationflags = 0x00000008 | 0x00000010
    det_proc = subprocess.Popen(
        cmd,
        stdout=None, stderr=None, stdin=None,
        creationflags=creationflags
    )

def stop_detector():
    global det_proc
    if det_proc and det_proc.poll() is None:
        try:
            det_proc.terminate()
        except:
            pass


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

try:
    console_init(root, max_lines=2000, auto_open=False)
    add_to_console(f"Console init OK")
except Exception as e:
    add_to_console(f"Console init FAILED: {e!r}")
    # You can return or continue depending on your tolerance.

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

status_frame = ctk.CTkFrame(root)
status_frame.grid(row=2, column=0, sticky="nsew", padx=(10,10), pady=(10,10))

screenshot_button = ctk.CTkButton(status_frame, text="Take Screenshot", command=on_take_screenshot)
screenshot_button.grid(row=0, column=0, sticky="nsew", padx=(10,0), pady=(0,10))

advanced_screenshot_button = ctk.CTkButton(status_frame, text="Take Advanced Screenshot", command=on_take_advanced_screenshot)
advanced_screenshot_button.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=(0,10))

auto_detection_button = ctk.CTkButton(status_frame, text="Activate Auto Detection", command=auto_detection)
auto_detection_button.grid(row=2, column=0, sticky="nsew", padx=(10,0), pady=(0,10))

root.after(50, lambda: (add_to_console("Navigating…"), safe_navigate()))

# def _on_close():
#     try:
#         keyboard.unhook_all()
#     finally:
#         root.destroy()

# Updated for overlay
def _on_close():
    """Stop detector if running, then close the app."""
    try:
        keyboard.unhook_all()
    finally:
        if det_proc and det_proc.poll() is None:
            stop_detector()     # <-- just stop, don't toggle
        root.destroy()           # close the GUI window


root.protocol("WM_DELETE_WINDOW", _on_close)
root.mainloop()
