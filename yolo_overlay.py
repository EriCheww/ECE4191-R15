import sys, time
import cv2
from ultralytics import YOLO
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject

"""
Yolo Overlay on GStreamer Video Stream
    Requirements:
        pip install ultralytics opencv-python-headless pycairo PyGObject
        and GStreamer installed and on PATH
"""

# --- CONFIG ---
UDP_PORT    = 5000          # must match your sender/relay
PAYLOAD_PT  = 96
CLOCK_RATE  = 90000
JITTER_MS   = 5
MODEL_PATH  = r"yolov11n.pt"   # <-- put your trained .pt here

# --- Init ---
Gst.init(None)
model = YOLO(MODEL_PATH)

# Build pipeline: udpsrc → jitterbuffer → depay → h264parse → avdec_h264 → videoconvert → appsink
pipe_str = (
    f'udpsrc port={UDP_PORT} '
    f'caps="application/x-rtp, media=video, encoding-name=H264, payload={PAYLOAD_PT}, clock-rate={CLOCK_RATE}" '
    f'! rtpjitterbuffer latency={JITTER_MS} '
    f'! rtph264depay ! h264parse ! avdec_h264 ! videoconvert '
    f'! appsink name=sink emit-signals=true drop=true sync=false max-buffers=1'
)
pipeline = Gst.parse_launch(pipe_str)
appsink  = pipeline.get_by_name("sink")

# Convert sample → numpy frame (BGR)
def get_frame(sample):
    buf = sample.get_buffer()
    caps = sample.get_caps()
    w = caps.get_structure(0).get_value('width')
    h = caps.get_structure(0).get_value('height')
    success, mapinfo = buf.map(Gst.MapFlags.READ)
    if not success:
        return None
    try:
        import numpy as np
        arr = np.frombuffer(mapinfo.data, dtype=np.uint8)
        frame = arr.reshape((h, w, 3))
        return frame
    finally:
        buf.unmap(mapinfo)

# Pull-mode: connect to new-sample signal
def on_new_sample(sink):
    sample = sink.emit("pull-sample")
    frame = get_frame(sample)
    if frame is None:
        return Gst.FlowReturn.OK

    # --- YOLO inference ---
    # results = model(frame, imgsz=640, conf=0.25, verbose=False)   # Ultralytics API also ok
    results = model.predict(frame, imgsz=640, conf=0.25, verbose=False)
    det = results[0]

    # --- draw boxes ---
    if det.boxes is not None:
        for b in det.boxes:
            xyxy = b.xyxy[0].tolist()
            cls  = int(b.cls[0].item())
            conf = float(b.conf[0].item())
            x1,y1,x2,y2 = map(int, xyxy)
            label = f"{det.names.get(cls, str(cls))} {conf:.2f}"
            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
            cv2.putText(frame, label, (x1, max(0,y1-6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2, cv2.LINE_AA)

    # show
    cv2.imshow("YOLO overlay (laptop)", frame)
    if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
        pipeline.set_state(Gst.State.NULL)
        cv2.destroyAllWindows()
        sys.exit(0)

    return Gst.FlowReturn.OK

appsink.connect("new-sample", on_new_sample)

# Run
print("[yolo_overlay] starting pipeline …")
pipeline.set_state(Gst.State.PLAYING)
# Simple GLib mainloop to drive GStreamer bus
loop = GObject.MainLoop()
try:
    loop.run()
except KeyboardInterrupt:
    pass
pipeline.set_state(Gst.State.NULL)
cv2.destroyAllWindows()