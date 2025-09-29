import customtkinter as ctk

def show_alert(parent, message: str, title: str = "Notice"):
    """Pop up an alert window centered over the parent window."""
    alert = ctk.CTkToplevel(parent)
    alert.title(title)
    alert.resizable(False, False)

    # Dimensions of the popup
    w, h = 300, 150

    # Get parent's position and size
    parent.update_idletasks()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    pw = parent.winfo_width()
    ph = parent.winfo_height()

    # Calculate center position
    x = px + (pw // 2) - (w // 2)
    y = py + (ph // 2) - (h // 2)

    # Apply geometry
    alert.geometry(f"{w}x{h}+{x}+{y}")

    # Center content
    frame = ctk.CTkFrame(alert)
    frame.pack(expand=True, fill="both", padx=10, pady=10)

    label = ctk.CTkLabel(frame, text=message, wraplength=250, justify="center")
    label.pack(pady=(20, 10))

    ok_button = ctk.CTkButton(frame, text="OK", command=alert.destroy)
    ok_button.pack(pady=(5, 10))

    # Keep alert on top and in front
    alert.transient(parent)   # stays on top of parent
    alert.grab_set()          # block interaction with parent
    alert.focus_force()       # grab keyboard focus
    alert.lift()              # bring to front
    alert.attributes("-topmost", True)  # force always on top
    alert.after_idle(alert.attributes, "-topmost", False)  # let it behave normally afterwards
