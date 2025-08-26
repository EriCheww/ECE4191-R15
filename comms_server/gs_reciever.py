# gs_receive_sub100.py
#!/usr/bin/env python3
import subprocess, signal, sys, shutil

PORT = 5000
JITTER_LATENCY_MS = 5
GST = shutil.which("gst-launch-1.0") or r"C:\Program Files\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe"

pipeline = (
    f'udpsrc port={PORT} '
    'caps="application/x-rtp, media=video, encoding-name=H264, payload=96, clock-rate=90000" '
    f'! rtpjitterbuffer latency={JITTER_LATENCY_MS} '
    '! rtph264depay '
    '! h264parse config-interval=-1 '
    '! d3d11h264dec '
    '! d3d11convert '
    '! d3d11videosink sync=false'
)

print(f"▶ Receiver: UDP {PORT}, jitter={JITTER_LATENCY_MS} ms")
print("  gst-launch-1.0 -q", pipeline)

def main():
    p = subprocess.Popen(f'"{GST}" -q {pipeline}', shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    def stop(*_):
        try: p.terminate()
        except: pass
        sys.exit(0)
    signal.signal(signal.SIGINT, stop)
    for line in p.stdout:
        if line.strip(): print(line.strip())
    sys.exit(p.wait() or 0)

if __name__ == "__main__":
    main()
