#!/usr/bin/env python3
import subprocess, signal, sys, shutil, time, os, http.server, socketserver, threading

# === Tunables (match your Pi sender) ===
PORT              = 5000
JITTER_LATENCY_MS = 5
PAYLOAD_PT        = 96
CLOCK_RATE        = 90000

# === Network (hotspot) ===
HOTSPOT_IP        = "192.168.137.1"   # Windows Mobile Hotspot default
WEB_PORT          = 8080              # HTTP for viewer
SIG_PORT          = 8443              # WS signaller
STREAM_NAME = "pi-cam"

# === Paths ===
GST = shutil.which("gst-launch-1.0") or r"C:\Program Files\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe"
WEB_DIR = "C:\\ECE4191\\gstreamer\\webrtcsink-webui"
# WEB_DIR = os.path.join(os.getcwd(), "webrtcsink-webui")
os.makedirs(WEB_DIR, exist_ok=True)
INDEX = os.path.join(WEB_DIR, "index.html")

# Simple HTTP server
import socket
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

def start_http_server():
    with socketserver.TCPServer(("0.0.0.0", WEB_PORT), Handler) as httpd:
        print(f"[http] serving {WEB_DIR} at http://{HOTSPOT_IP}:{WEB_PORT}/")
        httpd.serve_forever()

# GStreamer: webrtcsink signaller ONLY (we serve files via Python)
webrtc_branch = (
    "queue ! decodebin ! videoconvert "
    f'! webrtcsink '
      f'run-signalling-server=true '
      f'run-web-server=false '
      f'signalling-server-host=0.0.0.0 '
      f'signalling-server-port={SIG_PORT} '
      f'stun-server=stun://stun.l.google.com:19302 '
      f'video-caps=video/x-h264 '
      f'meta="meta,name={STREAM_NAME}" '

)
# preview_branch = "queue ! decodebin ! videoconvert ! autovideosink sync=false"

pipeline = (
    f'udpsrc port={PORT} '
    f'caps="application/x-rtp, media=video, encoding-name=H264, payload={PAYLOAD_PT}, clock-rate={CLOCK_RATE}" '
    f'! rtpjitterbuffer latency={JITTER_LATENCY_MS} '
    '! rtph264depay ! h264parse '
    '! tee name=t '
    f' t. ! {webrtc_branch} '
    # f' t. ! {preview_branch} '
)

def banner():
    print("▶ WebRTC relay (auto-start viewer)")
    print(f"  • Viewer page    : http://{HOTSPOT_IP}:{WEB_PORT}/")
    print(f"  • WS signaller   : ws://{HOTSPOT_IP}:{SIG_PORT}")
    print(f"  • UDP input      : {PORT} (RTP/H264), jitter={JITTER_LATENCY_MS} ms\n")
    print("Launching pipeline:")
    print(" ", GST)
    print(" ", pipeline, "\n")

def main():
    banner()
    t = threading.Thread(target=start_http_server, daemon=True)
    t.start()
    time.sleep(0.3)
    p = subprocess.Popen(f'"{GST}" -v {pipeline}', shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def stop(*_):
        try: p.terminate()
        except: pass
        time.sleep(0.3)
        try: p.kill()
        except: pass
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    for line in p.stdout:
        if line.strip():
            print(line.strip())
    sys.exit(p.wait() or 0)

if __name__ == "__main__":
    main()
