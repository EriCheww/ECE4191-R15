# viewer.py
# deps:
#   pip install tkwebview customtkinter keyboard

import atexit
import customtkinter as ctk
from tkwebview import TkWebview
import keyboard

from gui_utils.dropdown_sections import create_sections, collect_settings

HOME_URL = "http://192.168.137.1:8080/"  # hard-coded URL

PAD_X_LEFT = (10, 0)
PAD_X_MID  = (10, 10)
PAD_X_RIGHT= (0, 10)
PAD_Y_TOP = (10, 0)
PAD_Y_MID = (10, 10)
PAD_Y_BOT = (0, 10)

# --- global WASD hooks ---
def _print_key(ch: str):
    print(ch, flush=True)

keyboard.on_press_key("w", lambda e: _print_key("w"))
keyboard.on_press_key("a", lambda e: _print_key("a"))
keyboard.on_press_key("s", lambda e: _print_key("s"))
keyboard.on_press_key("d", lambda e: _print_key("d"))
atexit.register(keyboard.unhook_all)

# ---------- GUI ----------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title("Viewer")
root.geometry("1180x740")
root.grid_rowconfigure(0, weight=2)
root.grid_rowconfigure(1, weight=1)
root.grid_columnconfigure(0, weight=3)  # web
root.grid_columnconfigure(1, weight=1)  # settings

# Web browser container
web_frame = ctk.CTkFrame(root)
web_frame.grid(row=0, column=0, sticky="nsew", padx=PAD_X_LEFT, pady=PAD_Y_TOP)
web_frame.grid_rowconfigure(0, weight=1)
web_frame.grid_columnconfigure(0, weight=1)

web = TkWebview(web_frame)
web.grid(row=0, column=0, sticky="nsew")

# Right-side settings (make it scrollable if you expect many sections)
drop_down_settings_frame = ctk.CTkScrollableFrame(root, label_text="Settings")
drop_down_settings_frame.grid(row=0, column=1, sticky="nsew", padx=PAD_X_MID, pady=PAD_Y_TOP)
drop_down_settings_frame.grid_columnconfigure(0, weight=1)

# Build collapsible sections (each different)
configs = create_sections(
    drop_down_settings_frame,
    order=["Network", "Video", "Controls", "Diagnostics"],
    start_open="Network",
    layout="grid",
)

# A small footer area inside the settings column for actions
# settings = ctk.CTkFrame(drop_down_settings_frame)
# settings.grid(row=999, column=0, sticky="ew", padx=6, pady=(12, 6))  # large row idx to anchor at bottom
# ctk.CTkButton(settings, text="Print settings", command=lambda: print(collect_settings(configs))).pack(side="right", padx=6, pady=6)

status_frame = ctk.CTkFrame(root)
status_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=PAD_X_MID, pady=PAD_Y_MID)
status_frame.grid_rowconfigure(0, weight=1)
status_frame.grid_columnconfigure(0, weight=1)

status_label = ctk.CTkLabel(status_frame, text="STATUS Label")
status_label.pack(expand=True) 


# Open the homepage after UI is ready
root.after(50, lambda: web.navigate(HOME_URL))

def _on_close():
    try:
        keyboard.unhook_all()
    finally:
        root.destroy()

root.protocol("WM_DELETE_WINDOW", _on_close)
root.mainloop()
