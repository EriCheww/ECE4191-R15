# dropdown_sections.py
import customtkinter as ctk

# ----- Collapsible section helper (accordion) -----
def add_section(parent, title: str, start_open: bool = False,
                layout: str = "grid", **layout_kwargs):
    """
    Create a collapsible section inside `parent`.
    Returns (content_frame, toggle_fn).
    Safe to grid `wrapper` into parent while using pack inside it.
    """
    wrapper = ctk.CTkFrame(parent)

    if layout == "grid":
        defaults = dict(row=0, column=0, sticky="ew", padx=6, pady=6)
        defaults.update(layout_kwargs)
        wrapper.grid(**defaults)
    else:  # "pack"
        wrapper.pack(
            fill=layout_kwargs.get("fill", "x"),
            padx=layout_kwargs.get("padx", 6),
            pady=layout_kwargs.get("pady", 6),
        )

    state = {"open": start_open}
    header = ctk.CTkButton(wrapper, text="", anchor="w")
    content = ctk.CTkFrame(wrapper)

    def refresh():
        header.configure(text=f"{title} {'▾' if state['open'] else '▸'}")
        if state["open"]:
            content.pack(fill="x", padx=8, pady=(0, 8))
        else:
            content.pack_forget()

    def toggle():
        state["open"] = not state["open"]
        refresh()

    header.configure(command=toggle)
    header.pack(fill="x", padx=8, pady=8)
    refresh()

    return content, toggle

# ----- Per-section builders (customize freely) -----
def build_network(parent):
    out = {}
    row = ctk.CTkFrame(parent); row.pack(fill="x", pady=4)
    ctk.CTkLabel(row, text="Host").pack(side="left", padx=6)
    out["host"] = ctk.CTkEntry(row, placeholder_text="192.168.137.1")
    out["host"].pack(side="left", fill="x", expand=True, padx=6)

    row2 = ctk.CTkFrame(parent); row2.pack(fill="x", pady=4)
    ctk.CTkLabel(row2, text="Port").pack(side="left", padx=6)
    out["port"] = ctk.CTkEntry(row2, placeholder_text="5000", width=100)
    out["port"].pack(side="left", padx=6)
    out["proto"] = ctk.CTkOptionMenu(row2, values=["UDP/RTP", "WebRTC", "RTSP"])
    out["proto"].set("UDP/RTP"); out["proto"].pack(side="left", padx=6)

    out["test"] = ctk.CTkButton(
        parent, text="Test connection",
        command=lambda: print("Testing →", out["host"].get(), out["port"].get(), out["proto"].get())
    )
    out["test"].pack(pady=6)
    return out

def build_video(parent):
    out = {}
    row = ctk.CTkFrame(parent); row.pack(fill="x", pady=4)
    ctk.CTkLabel(row, text="Resolution").pack(side="left", padx=6)
    out["res"] = ctk.CTkComboBox(row, values=["640x480","1280x720","1920x1080"])
    out["res"].set("1280x720"); out["res"].pack(side="left", padx=6)

    row2 = ctk.CTkFrame(parent); row2.pack(fill="x", pady=4)
    ctk.CTkLabel(row2, text="Framerate").pack(side="left", padx=6)
    out["fps"] = ctk.CTkSlider(row2, from_=5, to=120, number_of_steps=115)
    out["fps"].set(30); out["fps"].pack(side="left", fill="x", expand=True, padx=6)

    out["lowlat"] = ctk.CTkCheckBox(parent, text="Low-latency mode")
    out["lowlat"].select(); out["lowlat"].pack(anchor="w", padx=6, pady=6)

    row3 = ctk.CTkFrame(parent); row3.pack(fill="x", pady=4)
    ctk.CTkLabel(row3, text="Encoder").pack(side="left", padx=6)
    out["enc"] = ctk.CTkOptionMenu(row3, values=["x264 (CPU)","NVENC","VAAPI","V4L2M2M","omxh264 (Pi)"])
    out["enc"].set("V4L2M2M"); out["enc"].pack(side="left", padx=6)
    return out

def build_controls(parent):
    out = {}
    out["invert"] = ctk.CTkCheckBox(parent, text="Invert Y-axis")
    out["invert"].pack(anchor="w", padx=6, pady=4)
    out["sens"] = ctk.CTkSlider(parent, from_=0, to=1, number_of_steps=100)
    out["sens"].set(0.5); out["sens"].pack(fill="x", padx=6, pady=6)
    out["pair"] = ctk.CTkButton(parent, text="Pair Controller")
    out["pair"].pack(padx=6, pady=6)
    return out

def build_diagnostics(parent):
    out = {}
    out["log"] = ctk.CTkTextbox(parent, height=120)
    out["log"].pack(fill="x", padx=6, pady=6)
    out["clear"] = ctk.CTkButton(parent, text="Clear",
                                 command=lambda: out["log"].delete("1.0","end"))
    out["clear"].pack(padx=6, pady=(0,6))
    return out

SECTION_BUILDERS = {
    "Network": build_network,
    "Video": build_video,
    "Controls": build_controls,
    "Diagnostics": build_diagnostics,
}

def create_sections(parent, order=None, start_open="Network",
                    layout="grid"):
    """
    Create multiple sections inside `parent` and return a dict of widget handles.
    """
    order = order or list(SECTION_BUILDERS.keys())
    parent.grid_columnconfigure(0, weight=1)
    configs = {}
    for i, name in enumerate(order):
        content, _toggle = add_section(
            parent, name, start_open=(name == start_open),
            layout=layout, row=i, column=0, sticky="ew"
        )
        configs[name] = SECTION_BUILDERS[name](content)
    return configs

def collect_settings(configs):
    """Example accessor that reads common settings safely."""
    out = {}
    if "Network" in configs:
        net = configs["Network"]
        out.update({
            "host": net["host"].get(),
            "port": net["port"].get(),
            "protocol": net["proto"].get(),
        })
    if "Video" in configs:
        vid = configs["Video"]
        out.update({
            "resolution": vid["res"].get(),
            "fps": int(vid["fps"].get()),
            "low_latency": bool(vid["lowlat"].get()),
            "encoder": vid["enc"].get(),
        })
    if "Controls" in configs:
        ctl = configs["Controls"]
        out.update({
            "invert_y": bool(ctl["invert"].get()),
            "sensitivity": float(ctl["sens"].get()),
        })
    return out
