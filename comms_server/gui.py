import customtkinter as ctk
from gui_utils.snapshot_capture import snapshot_by_title

TITLE_DEFAULT = "Direct3D11 renderer"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Snapshot d3d11videosink (client-only)")
        self.geometry("480x170")

        frame = ctk.CTkFrame(self); frame.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(frame, text="Window title contains:").grid(row=0, column=0, sticky="w", padx=8, pady=(10,4))
        self.title_hint = ctk.CTkEntry(frame, width=320); self.title_hint.insert(0, TITLE_DEFAULT)
        self.title_hint.grid(row=0, column=1, sticky="we", padx=8, pady=(10,4))

        self.status = ctk.CTkLabel(frame, text="Ready. Start your gst-launch viewer first.")
        self.status.grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=6)

        ctk.CTkButton(frame, text="Take snapshot", command=self.on_snap).grid(row=2, column=0, columnspan=2, pady=10)
        frame.grid_columnconfigure(1, weight=1)

    def on_snap(self):
        hint = self.title_hint.get().strip()
        try:
            path = snapshot_by_title(hint, bring_front=True, focus_delay=0.08, save_dir="snapshots")
            self.status.configure(text=f"✅ Saved {path.resolve()}")
        except Exception as e:
            self.status.configure(text=f"❌ {e}")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()
