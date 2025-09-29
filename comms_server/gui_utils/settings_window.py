from __future__ import annotations
import customtkinter as ctk
from tkinter import filedialog as fd
from typing import Callable, Dict, Optional, List

import gui_utils.app_settings as cfg
from gui_utils.console_window import add_to_console, init as console_init
from gui_utils.alert import show_alert

def digits_only(s: str) -> str:
    s = "" if s is None else str(s)
    return "".join(ch for ch in s if ch.isdigit())

# ------------------------ Two-way binding helper -----------------------------
class VarBinding:
    """Bind a Tk variable to a settings key (manual save)."""
    def __init__(self, key: str, var: ctk.Variable, *, transform_out: Callable[[str], str] | None = None):
        self.key = key
        self.var = var
        self.transform_out = transform_out
        self._updating = False

        # init var from settings
        self.var.set(cfg.settings.get(key))

        # NOTE: we do NOT subscribe to external changes while editing,
        # to avoid clobbering in-progress user edits.

        # just track user edits; do NOT persist here
        self._trace_id = self.var.trace_add("write", self._on_var_write)

    def _on_var_write(self, *_):
        # mark dirty on parent window if present
        try:
            # Walk up to the SettingsWindowManager via a bound method, if you like.
            pass
        except Exception:
            pass

    def save(self):
        value = self.var.get()
        if self.transform_out:
            value = self.transform_out(value)
        cfg.settings.set(self.key, value, persist=True, notify=True)

    def cleanup(self):
        try:
            self.var.trace_remove("write", self._trace_id)
        except Exception:
            pass


# ------------------------ Manager (console-style) ----------------------------
class SettingsWindowManager:
    def __init__(self, parent: Optional[ctk.CTk] = None):
        self.parent: Optional[ctk.CTk] = parent
        self._win: Optional[ctk.CTkToplevel] = None
        self._sidebar: Optional[ctk.CTkFrame] = None
        self._content: Optional[ctk.CTkFrame] = None

        # Sidebar buttons (for disabling the active one)
        self._buttons: Dict[str, ctk.CTkButton] = {}

        # Hard-coded pages (frames) – created lazily
        self._page_screenshots: Optional[ctk.CTkFrame] = None
        self._page_console: Optional[ctk.CTkFrame] = None

        # Vars + bindings (create once and reuse)
        self._dir_var: Optional[ctk.StringVar] = None
        self._prefix_var: Optional[ctk.StringVar] = None
        self._console_len_var: Optional[ctk.StringVar] = None  
        self._bindings: List[VarBinding] = []

        self._current_page: Optional[str] = None
        self._default_page = "Screenshots"

    def _raise_and_focus(self):
        w = self._win
        if not w or not w.winfo_exists():
            return
        try:
            w.deiconify()
            w.lift()
            w.focus_force()
            # Brief topmost toggle (same trick Console uses)
            w.attributes("-topmost", True)
            w.after(200, lambda: w.attributes("-topmost", False))
            w.after_idle(lambda: (w.lift(), w.focus_force()))
        except Exception:
            pass

    def attach(self, parent: ctk.CTk):
        self.parent = parent

    def open(self, page: Optional[str] = None):
        if self._win is not None and self._win.winfo_exists():
            if page:
                self.show_page(page)
            return

        if self.parent is None:
            raise RuntimeError("SettingsWindowManager has no parent. Call attach(root) or init(parent).")

        self._win = ctk.CTkToplevel(self.parent)
        self._win.title("Settings")
        self._win.geometry("860x520")
        self._win.resizable(True, True)
        self._win.protocol("WM_DELETE_WINDOW", self.close)
             
        self._win.lift()
        self._raise_and_focus()

        # Layout: sidebar | content
        self._win.grid_columnconfigure(0, weight=0)
        self._win.grid_columnconfigure(1, weight=1)
        self._win.grid_rowconfigure(0, weight=1)

        # Sidebar (hard-coded buttons)
        self._sidebar = ctk.CTkFrame(self._win, fg_color="transparent")
        self._sidebar.grid(row=0, column=0, sticky="nsw", padx=(10, 0), pady=(10, 10))
        self._sidebar.grid_propagate(False)
        self._sidebar.grid_columnconfigure(0, weight=1)

        btn_sc = ctk.CTkButton(self._sidebar, text="Screenshots", command=lambda: self.show_page("Screenshots"))
        btn_sc.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        btn_console = ctk.CTkButton(self._sidebar, text="Console", command=lambda: self.show_page("Console"))
        btn_console.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self._buttons = {"Screenshots": btn_sc, "Console": btn_console}
        self._sidebar.grid_rowconfigure(99, weight=1)  # push buttons to top
        
        self._save = ctk.CTkFrame(self._win, fg_color="transparent")
        self._save.grid(row=1, column=0, sticky="sew", padx=(10,0), pady=(0,10))
        self._save.grid_columnconfigure(0, weight=1)

        btn_save = ctk.CTkButton(self._save, text="Save", command=self._save_all)
        btn_save.grid(row=0, column=0, padx=(0,0), pady=(0,0), sticky="ew")

        # Content container
        self._content = ctk.CTkFrame(self._win)
        self._content.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(10, 10), pady=(10, 10))
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        # Show requested/default page (created lazily)
        self.show_page(page or self._default_page)

    def is_open(self) -> bool:
        return bool(self._win and self._win.winfo_exists())

    def show_page(self, name: str):
        if not self._content or not self._content.winfo_exists():
            return

        # Ensure the target page exists (lazy-create)
        if name == "Screenshots":
            self._ensure_page_screenshots()
            target = self._page_screenshots
        elif name == "Console":
            self._ensure_page_console()
            target = self._page_console
        else:
            return  # unknown page name

        # Hide others SAFELY (widgets may have been destroyed on previous close)
        self._safe_forget(self._page_screenshots if name != "Screenshots" else None)
        self._safe_forget(self._page_console    if name != "Console"     else None)

        # Show target (if it exists)
        if target is not None and target.winfo_exists():
            target.grid(row=0, column=0, sticky="nsew")
            self._current_page = name

        # Update button states
        for n, b in self._buttons.items():
            b.configure(state=("disabled" if n == name else "normal"))

    def close(self):
        if self._win is not None and self._win.winfo_exists():
            try:
                self._win.grab_release()
            except Exception:
                pass
            self._win.destroy()

        self._win = None
        self._sidebar = None
        self._content = None
        self._current_page = None

        # IMPORTANT: drop destroyed frame refs
        self._page_screenshots = None
        self._page_console = None

        # keep StringVars/_bindings so they can be reused next open
        self._buttons.clear()

    # ---------- internals ----------
    def _save_all(self):
        """Write current values to settings and confirm to console."""
        try:
            # Ensure vars exist even if user never opened a page in this session
            if self._dir_var is None:
                self._dir_var = ctk.StringVar(value=cfg.settings.get("ss_save_directory"))
                self._bindings.append(VarBinding("ss_save_directory", self._dir_var))
            if self._prefix_var is None:
                self._prefix_var = ctk.StringVar(value=cfg.settings.get("ss_user_prefix"))
                self._bindings.append(VarBinding("ss_user_prefix", self._prefix_var))
            if self._console_len_var is None:
                self._console_len_var = ctk.StringVar(value=cfg.settings.get("console_log_length"))
                self._bindings.append(VarBinding("console_log_length", self._console_len_var, transform_out=digits_only))

            # Persist all known bindings
            for b in self._bindings:
                b.save()

            # Apply console buffer size now
            try:
                raw = self._console_len_var.get() or cfg.settings.get("console_log_length") or "2000"
                max_lines = int(raw) if raw.isdigit() else 2000
                # clamp to a sane range
                max_lines = max(100, min(50000, max_lines))
                # Reconfigure the console buffer size (no auto-open side effects)
                if self.parent is not None:
                    console_init(self.parent, max_lines=max_lines, auto_open=False)
            except Exception as e:
                add_to_console(f"Warning: could not apply console size: {e!r}")

            # Feedback + keep focus on settings
            add_to_console(
                "Settings saved:\n"
                f" - ss_save_directory   = {self._dir_var.get() or '(empty)'}\n"
                f" - ss_user_prefix      = {self._prefix_var.get() or '(empty)'}\n"
                f" - console_log_length  = {self._console_len_var.get() or '(empty)'}"
            )

            show_alert(self._win, "Settings Saved!", "Success!")
            
            if self._win and self._win.winfo_exists():
                self._win.lift()
                self._win.focus_force()

        except Exception as e:
            add_to_console(f"Error saving settings: {e!r}")


    def _safe_forget(self, w):
        try:
            if w is not None and w.winfo_exists():
                w.grid_forget()
        except Exception:
            pass

    # ---------- hard-coded page creators (lazy) ----------
    def _ensure_page_screenshots(self):
        if self._page_screenshots is not None:
            return
        assert self._content is not None

        f = ctk.CTkFrame(self._content, fg_color="transparent")
        f.grid(padx=(10,10), pady=(10,10))
        f.grid_columnconfigure(1, weight=1)

        title_label = ctk.CTkLabel(f, text="Screenshots", font=ctk.CTkFont(size=18, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=(10,10), pady=(10, 10))

        # Ensure we reuse the same StringVars across reopens
        if self._dir_var is None:
            self._dir_var = ctk.StringVar()
            self._bindings.append(VarBinding("ss_save_directory", self._dir_var))

        if self._prefix_var is None:
            self._prefix_var = ctk.StringVar()
            self._bindings.append(VarBinding("ss_user_prefix", self._prefix_var))

        # Folder row
        folder_label = ctk.CTkLabel(f, text="Save folder:")
        folder_label.grid(row=1, column=0, padx=(10, 10), pady=(10,10))
        dir_entry = ctk.CTkEntry(f, textvariable=self._dir_var)
        dir_entry.grid(row=1, column=1, padx=(10,0), pady=(10,10), sticky="ew")
        btn_browse = ctk.CTkButton(f, text="Browse…", command=lambda: self._pick_dir(self._dir_var))
        btn_browse.grid(row=1, column=2, padx=(10, 10), pady=(10,10))
        hint0 = ctk.CTkLabel(f, text="Set the save path for the Take Screenshot button.", text_color=("gray50","gray70"))
        hint0.grid(row=2, column=0, columnspan=2, padx=(10,10), pady=(0,10), sticky="w")

        # Prefix row
        prefix_label = ctk.CTkLabel(f, text="User prefix:")
        prefix_label.grid(row=3, column=0, padx=(10, 10), pady=(10,10))
        entry_prefix = ctk.CTkEntry(f, textvariable=self._prefix_var)
        entry_prefix.grid(row=3, column=1, columnspan=2, padx=(10,10), pady=(10,10), sticky="ew")
        hint1 = ctk.CTkLabel(f, text="Set the naming convention for the saved screenshots: PREFIX_timestamp.", text_color=("gray50","gray70"))
        hint1.grid(row=4, column=0, columnspan=2, padx=(10,10), pady=(0,10), sticky="w")

        self._page_screenshots = f

    def _ensure_page_console(self):
        if self._page_console is not None:
            return
        assert self._content is not None

        f = ctk.CTkFrame(self._content, fg_color="transparent")
        f.grid(padx=(10,10), pady=(10,10))
        f.grid_columnconfigure(1, weight=1)

        title_label = ctk.CTkLabel(f, text="Console", font=ctk.CTkFont(size=18, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=3, sticky="w", padx=(10,10), pady=(10, 10))

        # --- Console max length (lines) ---
        if self._console_len_var is None:
            self._console_len_var = ctk.StringVar()
            # Bind to settings key 'console_log_length' and sanitize to digits on save
            self._bindings.append(VarBinding("console_log_length", self._console_len_var, transform_out=digits_only))

        length_label = ctk.CTkLabel(f, text="Console Log Max Length (lines):")
        length_label.grid(row=1, column=0, padx=(10,10), pady=(10,10), sticky="w")

        length_entry = ctk.CTkEntry(f, textvariable=self._console_len_var)
        length_entry.grid(row=1, column=1, padx=(10,10), pady=(10,10), sticky="ew")

        hint = ctk.CTkLabel(f, text="How many lines to keep in memory (default 2000).", text_color=("gray50","gray70"))
        hint.grid(row=2, column=0, columnspan=2, padx=(10,10), pady=(0,10), sticky="w")

        self._page_console = f


    # ---------- utils ----------
    def _pick_dir(self, var: ctk.StringVar):
        # Parent to settings window so focus returns here, not to the root
        chosen = fd.askdirectory(
            parent=self._win,                      # <-- key line
            initialdir=var.get() or None,
            mustexist=True,
            title="Select Screenshot Folder"
        )
        if chosen:
            var.set(chosen)

        # Make sure Settings regains focus after the native dialog
        if self._win is not None and self._win.winfo_exists():
            self._win.lift()
            self._win.focus_force()


# ------------------------ Optional: module-level singleton --------------------
_settings = SettingsWindowManager()
_default_parent: Optional[ctk.CTk] = None

def init(parent: ctk.CTk):
    """Initialize default parent (console-style)."""
    global _default_parent
    _default_parent = parent
    _settings.attach(parent)

def open_settings(page: Optional[str] = None):
    """Open (or focus) the settings window; optionally switch to a page."""
    parent = _default_parent
    if parent is None:
        raise RuntimeError("settings_window.init(parent) must be called first, or pass parent via _settings.attach().")
    _settings.open(page=page)

def open_settings_page(name: str):
    """Open (if needed) and show a page by name."""
    if not _settings.is_open():
        open_settings(page=name)
    else:
        _settings.show_page(name)

def is_settings_open() -> bool:
    return _settings.is_open()

def close_settings():
    _settings.close()
