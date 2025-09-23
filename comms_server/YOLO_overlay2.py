#!/usr/bin/env python3
"""
YOLO overlay for RTP/H264 via SDP (OpenCV/FFmpeg, Windows-friendly).
- Subscribes to udp://127.0.0.1:<--port> (RTP/H.264 via SDP)
- Runs Ultralytics YOLO on frames
- Draws boxes in an OpenCV window (separate from your WebRTC viewer)
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import sys
import time
import signal
import argparse
import threading
from collections import deque

import cv2
from ultralytics import YOLO
from pathlib import Path
# ---- CLI ----
p = argparse.ArgumentParser(description="YOLO overlay on local RTP/H264 (OpenCV/FFmpeg)")
p.add_argument("--port", type=int, default=5600, help="UDP port for local RTP/H264 input")
p.add_argument("--pt", type=int, default=96, help="RTP payload type")
p.add_argument("--clock-rate", dest="clock_rate", type=int, default=90000)
p.add_argument("--model", type=str, default="best.pt")
p.add_argument("--conf", type=float, default=0.25)
p.add_argument("--latency-ms", dest="latency_ms", type=int, default=40)  # accepted (unused)
args = p.parse_args()

# ---- CPU contention control (keeps GUI/receiver smooth) ----
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
try:
    cv2.setNumThreads(1)
except Exception:
    pass

# ---- Minimise FFmpeg/OpenCV buffering for RTP ----
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "protocol_whitelist;file,udp,rtp|"
    "buffer_size;102400|"
    "max_delay;0|"
    "fflags;nobuffer|"
    "flags;low_delay|"
    "reorder_queue_size;0"
)

# ---- Build a clean SDP (NO leading spaces), matching rtph264pay ----
SDP = f"""v=0
o=- 0 0 IN IP4 127.0.0.1
s=yolo-rtp
c=IN IP4 127.0.0.1
t=0 0
m=video {args.port} RTP/AVP {args.pt}
a=rtpmap:{args.pt} H264/{args.clock_rate}
a=fmtp:{args.pt} packetization-mode=1
"""
sdp_path = Path(os.getcwd(), "yolo_in.sdp")
with open(sdp_path, "w", newline="\n") as f:
    f.write(SDP)


# Build a capture URL with full protocol whitelist so FFmpeg can read RTP
# sdp_url = "file:/" + sdp_path.as_posix() + (
#     "?protocol_whitelist=file,udp,rtp,tcp,crypto,data"
#     "&fflags=nobuffer&flags=low_delay&max_delay=0"
#     "&reorder_queue_size=0&buffer_size=100000&fifo_size=100000"
# )

base_uri = sdp_path.as_uri()  # e.g., file:///C:/Users/.../yolo_in.sdp
sdp_url  = (
    base_uri
    + "?protocol_whitelist=file,udp,rtp,tcp,crypto,data"
      "&fflags=nobuffer&flags=low_delay&max_delay=0"
      "&reorder_queue_size=0&buffer_size=100000&fifo_size=100000"
)

print("[debug] SDP capture URL =", sdp_url)
cap = cv2.VideoCapture(sdp_url, cv2.CAP_FFMPEG)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)


# Wait briefly for socket/bind to be ready
for _ in range(300):  # ~3s
    if cap.isOpened():
        break
    time.sleep(0.01)
if not cap.isOpened():
    raise RuntimeError(
        f"[yolo_overlay] Failed to open RTP via SDP at {sdp_path}. "
        f"Is the relay sending to 127.0.0.1:{args.port} (pt={args.pt})?"
    )

# ---- Load YOLO model ----
try:
    model = YOLO(args.model)
except Exception as e:
    print(f"[yolo_overlay] Failed to load model '{args.model}': {e}", file=sys.stderr)
    sys.exit(1)

CLASS_NAMES = model.names  # dict[int,str]

# ---- Newest-frame-only reader thread ----
frames = deque(maxlen=1)
_stop = threading.Event()

def _reader():
    miss = 0
    while not _stop.is_set():
        ok, f = cap.read()
        if not ok:
            miss += 1
            if miss > 200:  # ~2s
                time.sleep(0.01)
            continue
        miss = 0
        frames.append(f)

t = threading.Thread(target=_reader, daemon=True)
t.start()

def _graceful_exit(*_):
    _stop.set()

signal.signal(signal.SIGINT, _graceful_exit)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, _graceful_exit)

# ---- Inference pacing ----
TARGET_FPS = 12.0 #usually
MIN_DT = 1.0 / TARGET_FPS
last_t = 0.0

print(f"[yolo_overlay] Listening on udp://127.0.0.1:{args.port} (pt={args.pt}, clock={args.clock_rate})")
print(f"[yolo_overlay] Model: {args.model}, conf: {args.conf}")

last_draw = None  # reuse last annotated frame when skipping inference

while not _stop.is_set():
    if not frames:
        cv2.waitKey(1)
        continue

    frame = frames[-1]
    now = time.time()
    run_det = (now - last_t) >= MIN_DT

    if run_det:
        last_t = now
        # (Optional) resize for speed; comment out if you want native resolution
        h, w = frame.shape[:2]
        # Example: scale down if very wide
        if w > 1280:
            new_w = 1280
            new_h = int(h * (new_w / w))
            infer_img = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            infer_img = frame

        # Ultralytics inference (quiet)
        try:
            results = model(infer_img, conf=args.conf, verbose=False)
        except Exception as e:
            print(f"[yolo_overlay] Inference error: {e}", file=sys.stderr)
            results = None

        out = infer_img.copy()
        if results:
            r0 = results[0]
            boxes = getattr(r0, "boxes", None)
            if boxes is not None and len(boxes) > 0:
                # Convert to original frame coords if resized
                scale_x = frame.shape[1] / out.shape[1]
                scale_y = frame.shape[0] / out.shape[0]

                for box in boxes:
                    xyxy = box.xyxy.squeeze().tolist()
                    if isinstance(xyxy, float):  # rare squeeze to scalar; force list
                        xyxy = [float(box.xyxy[0,0]), float(box.xyxy[0,1]),
                                float(box.xyxy[0,2]), float(box.xyxy[0,3])]
                    x1, y1, x2, y2 = xyxy
                    # scale back to display frame
                    x1 = int(x1 * scale_x); y1 = int(y1 * scale_y)
                    x2 = int(x2 * scale_x); y2 = int(y2 * scale_y)

                    cls = int(box.cls.item()) if hasattr(box, "cls") else -1
                    conf = float(box.conf.item()) if hasattr(box, "conf") else 0.0
                    label = f"{CLASS_NAMES.get(cls, str(cls))} {conf:.2f}"

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, max(0, y1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
        last_draw = frame
        show = frame
    else:
        # Reuse last annotated frame if inference is skipped this tick
        show = last_draw if last_draw is not None else frame

    cv2.imshow("YOLO overlay", show)
    if cv2.waitKey(1) & 0xFF == 27:
        break

# ---- Cleanup ----
_stop.set()
try:
    t.join(timeout=0.5)
except Exception:
    pass
cap.release()
cv2.destroyAllWindows()
