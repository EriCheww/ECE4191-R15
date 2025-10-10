# yolo_frame_detector.py
# Requires: pip install ultralytics pillow

from typing import List, Tuple
from dataclasses import dataclass
from PIL import Image
import time

try:
    from ultralytics import YOLO
except Exception as e:
    YOLO = None


@dataclass
class Det:
    label: str
    conf: float
    x1: int; y1: int; x2: int; y2: int
    x1n: float; y1n: float; x2n: float; y2n: float

class YOLOFrameDetector:
    def __init__(self, model_path: str, **opts):
        self.conf = float(opts.get("conf", 0.25))
        self.iou  = float(opts.get("iou", 0.45))
        self.model = self._load_model(model_path)

    def _load_model(self, path: str):
        if YOLO is None:
            return None
        return YOLO(path)

    def _infer_pixels(self, img: Image.Image) -> List[Tuple[str, float, int, int, int, int]]:
        # Fallback: draw a visible box if YOLO isn’t loaded/installed yet
        if self.model is None:
            W, H = img.size
            w, h = int(W*0.4), int(H*0.4)
            x1, y1 = (W - w)//2, (H - h)//2
            return [("demo", 1.00, x1, y1, x1 + w, y1 + h)]

        res = self.model.predict(img, conf=self.conf, iou=self.iou, verbose=False)[0]
        out: List[Tuple[str, float, int, int, int, int]] = []
        names = getattr(self.model, "names", {})
        for b in res.boxes:
            x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
            cls = int(b.cls)
            label = names.get(cls, str(cls))
            conf  = float(b.conf)
            out.append((label, conf, x1, y1, x2, y2))
        return out

    def detect_image(self, img: Image.Image) -> List[Det]:
        W, H = img.size
        raw = self._infer_pixels(img)
        return [
            Det(label, conf, x1, y1, x2, y2,
                x1/W, y1/H, x2/W, y2/H)
            for (label, conf, x1, y1, x2, y2) in raw
        ]

    def detect_from_widget(self, grab_func) -> List[Det]:
        return self.detect_image(grab_func())


class RateLimiter:
    def __init__(self, fps: float = 10.0):
        self.min_dt = 1.0 / max(1e-6, fps)
        self.last_t = 0.0

    def ok(self) -> bool:
        t = time.perf_counter()
        if t - self.last_t >= self.min_dt:
            self.last_t = t
            return True
        return False
