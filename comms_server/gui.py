import atexit
import customtkinter as ctk
import keyboard
import time
import datetime
import os
import re
from tkinter import filedialog
from tkwebview import TkWebview
from gui_utils.collapsible_sections import create_sections
from gui_utils.screenshot import take_screenshot


##########################################################
# ---------------------- STYLE ---------------------------
##########################################################
HEADER_FONT = ("Arial", 14)





##########################################################
# ------------------- SETTINGS ---------------------------
##########################################################

HOME_URL = "http://192.168.137.1:8080/"

SS_SAVE_DIRECTORY = "C:\\ECE4191\\test_photos"
SS_USER_PREFIX = 'test'





##########################################################
# ------------------ FUNCTIONS ---------------------------
##########################################################

def print_key(ch: str):
    print(ch, flush=True)

def fresh_url(url: str) -> str:
    sep = '&' if '?' in url else '?'
    return f"{url}{sep}cb={int(time.time())}"

def timestamp():
    return datetime.datetime.now().strftime("%H:%M:%S")

def add_to_console(message: str):
    if not message or console_text is None:
        return

    def append():
        try:
            console_text.configure(state="normal")
            console_text.insert("end", f"[{timestamp()}] {message}\n")
            console_text.configure(state="disabled")
            console_text.see("end")
        except Exception:
            pass

    console_text.after(0, append)

def safe_navigate():
    try:
        web.navigate(fresh_url(HOME_URL))
        add_to_console("Connecting to stream...")
    except Exception as e:
        add_to_console("Error Loading URL")

def on_take_screenshot():
    success, result = take_screenshot(web, SS_SAVE_DIRECTORY, SS_USER_PREFIX)

    if success:
        add_to_console(f"Success!\n" f"Screenshot saved:\n{result}")
    else:
        add_to_console(f"Error!\n" f"Failed: {result}")
    
def sanitize_prefix(s: str) -> str:
    # Remove illegal filename chars and trim spaces
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", s).strip()

def set_name_prefix_from_entry(entry: ctk.CTkEntry = None):
    """Read text from entry, sanitize, and push into both the StringVar and global."""
    global SS_USER_PREFIX
    val = entry.get().strip() if entry else SS_USER_PREFIX_VAR.get().strip()
    val = sanitize_prefix(val)
    if not val:
        add_to_console("Invalid name! Please enter a non-empty prefix.")
        return
    SS_USER_PREFIX_VAR.set(val)  # updates any bound Entry
    SS_USER_PREFIX = val     
    add_to_console(f"Set {SS_USER_PREFIX} as SS pre-fix.")  

def choose_folder():
    """Open a folder picker and update SS_SAVE_DIRECTORY + the UI var."""
    global SS_SAVE_DIRECTORY
    initial = SS_SAVE_DIRECTORY_VAR.get() or os.path.expanduser("~")
    folder = filedialog.askdirectory(title="Select Screenshot Folder", initialdir=initial)
    if folder:
        # Normalize path to avoid mixed slashes (\t issues, etc.)
        folder = os.path.normpath(folder)
        SS_SAVE_DIRECTORY = folder
        SS_SAVE_DIRECTORY_VAR.set(folder)
        add_to_console(f"Changed photo path to: {SS_SAVE_DIRECTORY}")


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
root.grid_rowconfigure(0, weight=2)
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=3)  # web
root.grid_columnconfigure(1, weight=1)  # settings

SS_SAVE_DIRECTORY_VAR   = ctk.StringVar(value=SS_SAVE_DIRECTORY)
SS_USER_PREFIX_VAR = ctk.StringVar(value=SS_USER_PREFIX)

# Web browser container
web_frame = ctk.CTkFrame(root)
web_frame.grid(row=0, column=0, sticky="nsew", padx=(10,0), pady=(10,0))
web_frame.grid_rowconfigure(0, weight=1)
web_frame.grid_columnconfigure(0, weight=1)

web = TkWebview(web_frame)
web.grid(row=0, column=0, sticky="nsew")

# Right-side settings
settings_frame = ctk.CTkFrame(root)
settings_frame.grid(row=0, column=1, sticky="nsew", padx=(10,10), pady=(10,0))

settings_label = ctk.CTkLabel(settings_frame, text="Settings:", font=HEADER_FONT)
settings_label.pack(side="top", fill="x", padx=(10,10), pady=(10,0))

drop_down_settings_frame = ctk.CTkScrollableFrame(settings_frame, fg_color="transparent")
drop_down_settings_frame.pack(fill='both', expand=True, padx=(10,10), pady=(0,10))

# Build collapsible sections (each different)
def build_screenshot_settings(frame):
    # --- File name prefix (USER STRING) ---
    ctk.CTkLabel(frame, text="File name prefix (USER STRING):").pack(padx=(10,10), pady=(10,0), anchor="w")
    row1 = ctk.CTkFrame(frame, fg_color="transparent")
    row1.pack(fill="x", padx=(10,10), pady=(0, 10))
    name_entry = ctk.CTkEntry(row1, textvariable=SS_USER_PREFIX_VAR, placeholder_text="e.g. MyPiCam")
    name_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    name_button = ctk.CTkButton(row1, text="Set Name", command=set_name_prefix_from_entry)
    name_button.pack(side="right")

    # --- Output folder row ---
    ctk.CTkLabel(frame, text="Output folder:").pack(padx=(10,10), anchor="w")
    row2 = ctk.CTkFrame(frame, fg_color="transparent")
    row2.pack(fill="x", padx=(10,10), pady=(0, 10))

    # Read-only entry that shows the chosen folder
    folder_entry = ctk.CTkEntry(row2, textvariable=SS_SAVE_DIRECTORY_VAR, state="disabled")
    folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    # Browse button to choose folder
    browse_btn = ctk.CTkButton(row2, text="Choose folder…", command=choose_folder)
    browse_btn.pack(side="right")

def build_video(frame):
    ctk.CTkLabel(frame, text="Video Settings", fg_color="transparent").pack(pady=5)
    ctk.CTkEntry(frame, placeholder_text="Resolution").pack(pady=5)
    ctk.CTkEntry(frame, placeholder_text="Framerate").pack(pady=5)

def build_controls(frame):
    ctk.CTkLabel(frame, text="Control Panel", fg_color="transparent").pack(pady=5)
    ctk.CTkButton(frame, text="Start").pack(pady=5)
    ctk.CTkButton(frame, text="Stop").pack(pady=5)

def build_diagnostics(frame):
    ctk.CTkLabel(frame, text="Diagnostics", fg_color="transparent").pack(pady=5)
    ctk.CTkButton(frame, text="Run Check").pack(pady=5)

sections = create_sections(
    drop_down_settings_frame,
    sections={
        "Screenshot": build_screenshot_settings,
        "Video": build_video,
        "Controls": build_controls,
        "Diagnostics": build_diagnostics,
    },
    start_open="Network",  # Start with Network open
    layout="grid",
)

status_frame = ctk.CTkFrame(root)
status_frame.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=(10,10))
status_frame.grid_rowconfigure(0, weight=1)
status_frame.grid_columnconfigure(0, weight=1)

screenshot_button = ctk.CTkButton(status_frame, text="Take Screenshot", command=on_take_screenshot)
screenshot_button.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=(0,10))

# Create console inside bottom-right cell
console_frame = ctk.CTkFrame(root)
console_frame.grid(row=1, column=1, sticky="nsew", padx=(10,10), pady=(10,10))

console_label = ctk.CTkLabel(console_frame, text="Console:", font=HEADER_FONT)
console_label.pack(side="top", padx=(10,10), pady=(10,0))

console_text = ctk.CTkTextbox(console_frame, height=100, font=("Courier New", 12))
console_text.pack(fill="both", expand=True, padx=(10,10), pady=(10,10))
console_text.configure(state="disabled")

root.after(50, safe_navigate)

def _on_close():
    try:
        keyboard.unhook_all()
    finally:
        root.destroy()

root.protocol("WM_DELETE_WINDOW", _on_close)
root.mainloop()
