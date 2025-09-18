from __future__ import annotations
import datetime
import threading
from collections import deque
from pathlib import Path
import os

import customtkinter as ctk
from tkinter import filedialog as fd
from tkinter import messagebox as mb

import gui_utils.app_settings as cfg  

class ConsoleManager:

    def __init__(self, parent: ctk.CTk | None = None, *, max_lines: int = 2000, auto_open: bool = False):
        self.parent: ctk.CTk | None = parent
        self.max_lines = cfg.settings.get("console_log_length")
        self.auto_open = auto_open

        self._buffer = deque(maxlen=max_lines)
        self._lock = threading.Lock()

        self._win: ctk.CTkToplevel | None = None
        self._text: ctk.CTkTextbox | None = None
        self._last_save_dir: str | None = None

    # ---------- Public API ----------
    def attach(self, parent: ctk.CTk):
        """Attach the Tk parent (must be called after root is created)."""
        self.parent = parent

    def open(self):
        """Open the console window; if already open, just focus it."""
        if self._win is not None and self._win.winfo_exists():
            self._win.lift()
            self._win.focus_force()
            return

        if self.parent is None:
            raise RuntimeError("ConsoleManager has no parent. Call attach(root) or pass parent in the constructor.")

        self._win = ctk.CTkToplevel(self.parent)
        self._win.title("Console")
        self._win.geometry("700x450")
        self._win.protocol("WM_DELETE_WINDOW", self.close)

        self._text = ctk.CTkTextbox(self._win, wrap="word")
        self._text.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self._text.configure(state="normal")

        # Preload history
        with self._lock:
            if self._buffer:
                self._text.insert("end", "\n".join(self._buffer) + "\n")

        self._text.configure(state="disabled")
        self._text.see("end")

        # buttons row
        btn_row = ctk.CTkFrame(self._win, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(10, 10))

        btn_row.grid_columnconfigure(0, weight=1)  # left spacer (no widget needed)
        btn_row.grid_columnconfigure(4, weight=1)  # right spacer

        ctk.CTkButton(btn_row, text="Save…", command=self.save_dialog).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(btn_row, text="Clear", command=self.clear).grid(row=0, column=2, padx=8)
        ctk.CTkButton(btn_row, text="Close", command=self.close).grid(row=0, column=3, padx=(8, 0))
        
        self._raise_and_focus()


    def add(self, message: str):
        """Append a line to buffer and UI (thread-safe)."""
        if not message:
            return
        line = self._format(message)

        with self._lock:
            self._buffer.append(line)

        # If UI is open, append on the Tk thread
        if self._text is not None and self._text.winfo_exists():
            self._text.after(0, self._append_last_line_to_ui)
        elif self.auto_open and self.parent is not None:
            # Auto-open a console if not visible
            self.parent.after(0, self.open)

    def clear(self):
        """Clear buffer and UI."""
        with self._lock:
            self._buffer.clear()
        if self._text is not None and self._text.winfo_exists():
            def _clear():
                self._text.configure(state="normal")
                self._text.delete("1.0", "end")
                self._text.configure(state="disabled")
            self._text.after(0, _clear)

    def close(self):
        """Close the console window and release UI refs (buffer is kept)."""
        if self._win is not None and self._win.winfo_exists():
            self._win.destroy()
        self._win = None
        self._text = None

    def _raise_and_focus(self):
        w = self._win
        if not w or not w.winfo_exists():
            return
        try:
            w.deiconify()
            w.lift()
            w.focus_force()
            # brief topmost toggle in case something steals focus (e.g., webviews)
            w.attributes("-topmost", True)
            w.after(200, lambda: w.attributes("-topmost", False))
            w.after_idle(lambda: (w.lift(), w.focus_force()))
        except Exception:
            pass

    def is_open(self) -> bool:
        return bool(self._win and self._win.winfo_exists())

        # ---------- saving ----------
    def get_log_text(self) -> str:
        with self._lock:
            if not self._buffer:
                return ""
            return "\n".join(self._buffer) + "\n"

    def save_dialog(self):
        parent_win = self._win if (self._win and self._win.winfo_exists()) else self.parent
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested = f"console_{ts}.log"

        initialdir = self._last_save_dir or str(Path.home())
        path = fd.asksaveasfilename(
            parent=parent_win,
            title="Save Console Log",
            initialdir=initialdir,
            initialfile=suggested,
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.save_to_file(path)
            self._last_save_dir = os.path.dirname(path)
            self.add(f"Saved log to: {path}")
            # Optional: message box
            # mb.showinfo("Console", f"Saved log to:\n{path}", parent=parent_win)
        except Exception as e:
            mb.showerror("Save Failed", f"Could not save log:\n{e}", parent=parent_win)

    def save_to_file(self, path: str | os.PathLike):
        text = self.get_log_text()
        Path(path).write_text(text, encoding="utf-8")

    # ---------- Internals ----------
    def _append_last_line_to_ui(self):
        if self._text is None or not self._text.winfo_exists():
            return
        with self._lock:
            if not self._buffer:
                return
            last_line = self._buffer[-1]
        try:
            self._text.configure(state="normal")
            self._text.insert("end", last_line + "\n")
            self._text.configure(state="disabled")
            self._text.see("end")
        except Exception:
            pass

    @staticmethod
    def _timestamp() -> str:
        return datetime.datetime.now().strftime("%H:%M:%S")

    def _format(self, msg: str) -> str:
        return f"[{self._timestamp()}] {msg}"


# ---------- Optional: module-level singleton helpers ----------
# Import these in your app for a super simple API.
_console = ConsoleManager()

def init(parent: ctk.CTk, *, max_lines: int = 2000, auto_open: bool = False):
    """Initialize the singleton console manager with your root window."""
    _console.attach(parent)
    _console.max_lines = max_lines
    _console.auto_open = auto_open
    # Recreate the buffer with new capacity if needed
    if _console.max_lines != len(_console._buffer):
        _console._buffer = deque(_console._buffer, maxlen=max_lines)

def open_console():
    _console.open()

def add_to_console(message: str):
    _console.add(message)

def clear_console():
    _console.clear()

def close_console():
    _console.close()

def is_console_open() -> bool:
    return _console.is_open()
