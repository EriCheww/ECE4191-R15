import subprocess, sys, os
# …
def _start_detection():
    exe = sys.executable  # current python
    script = os.path.join(os.path.dirname(__file__), "yolo_overlay.py")
    subprocess.Popen([exe, script])

btn = ctk.CTkButton(drop_down_settings_frame, text="Start YOLO overlay",
                    command=_start_detection)
btn.grid(row=998, column=0, sticky="ew", padx=8, pady=(12, 6))
