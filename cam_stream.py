from flask import Flask, Response, render_template_string
from picamera2 import Picamera2
from io import BytesIO
from PIL import Image
import time

app = Flask(__name__)

# Tunables (adjust if needed)
WIDTH, HEIGHT = 1280, 720
FPS = 24
JPEG_QUALITY = 80  # 50–95 (lower = smaller)

PAGE = f"""<!doctype html>
<title>Pi Camera Stream</title>
<h1>Pi Camera Stream</h1>
<p>Resolution: {WIDTH}x{HEIGHT} @ {FPS} fps, JPEG quality {JPEG_QUALITY}</p>
<p><a href="/healthz">health</a></p>
<img src="/video" style="max-width:100%;height:auto;border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.12);" />
"""

@app.route("/")
def index():
    return render_template_string(PAGE)

@app.route("/healthz")
def healthz():
    return "ok", 200

# Initialise camera once
picam2 = Picamera2()
cfg = picam2.create_video_configuration(main={"size": (WIDTH, HEIGHT), "format": "RGB888"})
# Try to lock frame duration close to target FPS
min_us = int(1_000_000 / max(1, FPS))
cfg["controls"] = {"FrameDurationLimits": (min_us, min_us)}
picam2.configure(cfg)
picam2.start()
time.sleep(0.2)  # small warm-up

def mjpeg_generator():
    period = 1.0 / max(1, FPS)
    last = 0.0
    while True:
        now = time.time()
        dt = now - last
        if dt < period:
            time.sleep(period - dt)
        last = time.time()

        frame = picam2.capture_array()  # numpy RGB
        buf = BytesIO()
        Image.fromarray(frame).save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
        jpg = buf.getvalue()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")

@app.route("/video")
def video():
    return Response(mjpeg_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    # Bind to all interfaces so your laptop/phone can view it
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
