#!/usr/bin/env python3
import sys, argparse
import cv2
from ultralytics import YOLO
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject

import threading
import time

latest = {"frame": None}
lock = threading.Lock()


# -------- CLI --------
p = argparse.ArgumentParser(description="YOLO overlay on RTP/H.264 stream")
p.add_argument("--port", type=int, default=5600, help="UDP port for RTP/H264 input")
p.add_argument("--pt", type=int, default=96, help="RTP payload type")
p.add_argument("--clock-rate", dest="clock_rate", type=int, default=90000)
p.add_argument("--latency-ms", dest="latency_ms", type=int, default=5)
p.add_argument("--model", type=str, default="best.pt")
p.add_argument("--conf", type=float, default=0.25)
args = p.parse_args()

Gst.init(None)
model = YOLO(args.model)

pipe_str = (
    f'udpsrc port={args.port} '
    f'caps="application/x-rtp,media=video,encoding-name=H264,payload={args.pt},clock-rate={args.clock_rate}" '
    f'! rtpjitterbuffer latency={args.latency_ms} '
    f'! rtph264depay ! h264parse ! avdec_h264 ! videoconvert '
    f'! video/x-raw,format=BGR '                      # <-- add this
    f'! queue max-size-buffers=1 leaky=downstream '
    f'! appsink name=sink emit-signals=true drop=true sync=false max-buffers=1'
)


pipeline = Gst.parse_launch(pipe_str)

# ===== Grabbing appsink and connecting the non-blocking callback =====
appsink = pipeline.get_by_name("sink")
appsink.set_property("emit-signals", True)

def _get_frame(sample):
    buf = sample.get_buffer()
    caps = sample.get_caps()
    w = caps.get_structure(0).get_value('width')
    h = caps.get_structure(0).get_value('height')
    ok, mapinfo = buf.map(Gst.MapFlags.READ)
    if not ok:
        return None
    try:
        import numpy as np
        arr = np.frombuffer(mapinfo.data, dtype=np.uint8)
        return arr.reshape((h, w, 3)).copy()  # <-- copy()
    finally:
        buf.unmap(mapinfo)


def on_new_sample(sink):
    sample = sink.emit("pull-sample")
    frame = _get_frame(sample)
    if frame is not None:
        with lock:
            latest["frame"] = frame
    return Gst.FlowReturn.OK

appsink.connect("new-sample", on_new_sample)

# ====== old implementation of appsink =============
# appsink  = pipeline.get_by_name("sink")

# def _get_frame(sample):
#     buf = sample.get_buffer()
#     caps = sample.get_caps()
#     w = caps.get_structure(0).get_value('width')
#     h = caps.get_structure(0).get_value('height')
#     ok, mapinfo = buf.map(Gst.MapFlags.READ)
#     if not ok:
#         return None
#     try:
#         import numpy as np
#         arr = np.frombuffer(mapinfo.data, dtype=np.uint8)
#         return arr.reshape((h, w, 3))
#     finally:
#         buf.unmap(mapinfo)

# def on_new_sample(sink):
#     sample = sink.emit("pull-sample")
#     frame = _get_frame(sample)
#     if frame is None:
#         return Gst.FlowReturn.OK

#     # YOLO inference
#     det = model.predict(frame, imgsz=640, conf=args.conf, verbose=False)[0]

#     # Draw boxes
#     if det.boxes is not None:
#         for b in det.boxes:
#             x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
#             cls = int(b.cls[0].item()) if b.cls is not None else -1
#             conf = float(b.conf[0].item()) if b.conf is not None else 0.0
#             label = f"{det.names.get(cls, str(cls))} {conf:.2f}"
#             cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
#             cv2.putText(frame, label, (x1, max(0,y1-6)),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2, cv2.LINE_AA)

#     cv2.imshow("YOLO overlay", frame)
#     if cv2.waitKey(1) & 0xFF == 27:  # ESC
#         pipeline.set_state(Gst.State.NULL)
#         cv2.destroyAllWindows()
#         sys.exit(0)
#     return Gst.FlowReturn.OK

# appsink.connect("new-sample", on_new_sample)

# ===== Thread to run inference loop =====
loop = GObject.MainLoop()

def infer_loop():
    while True:
        with lock:
            frame = latest["frame"]; latest["frame"] = None
        if frame is None:
            time.sleep(0.005); continue

        det = model.predict(frame, imgsz=640, conf=args.conf, verbose=False)[0]
        if det.boxes is not None:
            for b in det.boxes:
                x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())
                cls  = int(b.cls[0].item()) if b.cls is not None else -1
                conf = float(b.conf[0].item()) if b.conf is not None else 0.0
                label = f"{det.names.get(cls, str(cls))} {conf:.2f}"
                cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
                cv2.putText(frame, label, (x1, max(0,y1-6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2, cv2.LINE_AA)

        cv2.imshow("YOLO overlay", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            GObject.idle_add(loop.quit)  # <-- stop main loop
            break

t = threading.Thread(target=infer_loop, daemon=True)
t.start()

pipeline.set_state(Gst.State.PLAYING)
try:
    loop.run()
finally:
    pipeline.set_state(Gst.State.NULL)
    cv2.destroyAllWindows()

# print(f"[yolo_overlay] model={args.model} port={args.port} conf={args.conf}")
# pipeline.set_state(Gst.State.PLAYING)
# loop = GObject.MainLoop()
# try:
#     loop.run()
# except KeyboardInterrupt:
#     pass
# pipeline.set_state(Gst.State.NULL)
# cv2.destroyAllWindows()
