from pathlib import Path
from datetime import datetime
from typing import Tuple, Union
from PIL import ImageGrab  # pip install pillow


def take_screenshot(widget, save_dir: str | Path, name: str) -> Tuple[bool, Union[Path, str]]:
    """
    Capture a screenshot of a Tkinter widget (e.g., tkwebview2.WebView2)
    and save it to a specified directory.

    Args:
        widget: The Tkinter widget to capture (e.g., your web view).
        save_dir: The directory where the screenshot should be saved.
        name: The user-provided prefix for the screenshot name.

    Returns:
        Tuple[bool, Union[Path, str]]:
            - (True, Path) if saved successfully.
            - (False, "error message") if something failed.
    """
    try:
        # Validate inputs
        name = name.strip()
        if not name:
            return False, "Name cannot be empty."

        save_dir = Path(save_dir).expanduser().resolve()
        if not save_dir.exists():
            try:
                save_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"Failed to create directory: {e}"

        # Ensure widget geometry is up-to-date
        try:
            widget.update_idletasks()
        except Exception:
            pass

        # Get widget's position on screen
        try:
            x1 = widget.winfo_rootx()
            y1 = widget.winfo_rooty()
            x2 = x1 + widget.winfo_width()
            y2 = y1 + widget.winfo_height()
        except Exception as e:
            return False, f"Failed to calculate widget dimensions: {e}"

        # Build filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        save_path = save_dir / filename

        # Take screenshot
        try:
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            img.save(save_path)
        except Exception as e:
            return False, f"Failed to capture screenshot: {e}"

        return True, save_path

    except Exception as e:
        return False, f"Unexpected error: {e}"
