import time, datetime, ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Optional, Tuple

import mss
from PIL import Image

# ---- DPI awareness (so coordinates match pixels on HiDPI) ----
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ---- WinAPI we use ----
user32 = ctypes.WinDLL("user32", use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
SW_RESTORE = 9
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOOWNERZORDER = 0x0200
SWP_SHOWWINDOW = 0x0040

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

# prototypes (64-bit safe)
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype  = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype  = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype  = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype  = ctypes.c_int
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype  = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ClientToScreen.restype  = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype  = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype  = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.SetWindowPos.restype  = wintypes.BOOL

# ---- helpers ----
def _get_title(hwnd) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0: return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value

def _client_rect_screen(hwnd) -> Tuple[int, int, int, int]:
    rc = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rc)): return (0,0,0,0)
    pt = POINT(0,0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(pt)): return (0,0,0,0)
    left, top = pt.x, pt.y
    return (left, top, left + (rc.right - rc.left), top + (rc.bottom - rc.top))

def find_window_by_title_substring(substr: str) -> Optional[Tuple[int, str]]:
    """Return (hwnd, title) of the largest visible window whose title contains substr (case-insensitive)."""
    substr = (substr or "").lower()
    found = []

    @EnumWindowsProc
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _get_title(hwnd)
        if substr and substr in title.lower():
            l,t,r,b = _client_rect_screen(hwnd)
            w,h = r-l, b-t
            if w>0 and h>0:
                found.append((hwnd, title, w*h))
        return True

    user32.EnumWindows(cb, 0)
    if not found:
        return None
    found.sort(key=lambda x: x[2], reverse=True)
    hwnd, title, _ = found[0]
    return hwnd, title

def bring_to_front(hwnd: int):
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0,0,0,0,
                        SWP_NOMOVE|SWP_NOSIZE|SWP_NOOWNERZORDER|SWP_SHOWWINDOW)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0,0,0,0,
                        SWP_NOMOVE|SWP_NOSIZE|SWP_NOOWNERZORDER|SWP_SHOWWINDOW)

def capture_client(hwnd: int) -> Image.Image:
    """Capture client area (no borders) as a PIL Image (RGB)."""
    l,t,r,b = _client_rect_screen(hwnd)
    w,h = r-l, b-t
    if w<=0 or h<=0:
        raise RuntimeError("client area is empty")
    with mss.mss() as sct:
        shot = sct.grab({"left": l, "top": t, "width": w, "height": h})
        return Image.frombytes("RGB", (shot.width, shot.height), shot.rgb)

def save_image(img: Image.Image, save_dir: Path | str = "snapshots",
               prefix: str = "snapshot") -> Path:
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    p = save_dir / f"{prefix}_{ts}.png"
    img.save(p)
    return p

def snapshot_by_title(title_substr: str, *,
                      bring_front: bool = True,
                      focus_delay: float = 0.08,
                      save_dir: Path | str = "snapshots") -> Path:
    """Find window by title substring, optionally foreground it, capture client area, save PNG, return path."""
    res = find_window_by_title_substring(title_substr)
    if not res:
        raise RuntimeError(f"window with title containing {title_substr!r} not found")
    hwnd, _title = res
    if bring_front:
        bring_to_front(hwnd)
        time.sleep(focus_delay)
    img = capture_client(hwnd)
    return save_image(img, save_dir=save_dir)

# ---- optional CLI ----
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Capture client area of a window by title substring")
    ap.add_argument("--title", required=True, help="substring to match in window title (e.g. d3d11videosink)")
    ap.add_argument("--out", default="snapshots", help="output directory")
    ap.add_argument("--no-bring-front", action="store_true", help="do not foreground the window before capture")
    ap.add_argument("--delay", type=float, default=0.08, help="delay after focus before capture")
    args = ap.parse_args()

    path = snapshot_by_title(args.title,
                             bring_front=not args.no_bring_front,
                             focus_delay=args.delay,
                             save_dir=args.out)
    print(f"saved: {path.resolve()}")
