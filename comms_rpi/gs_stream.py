#!/usr/bin/env python3
import subprocess, signal, sys, shutil

LAPTOP_IP = "192.168.137.1"  # <-- set this
PORT = 5000
WIDTH, HEIGHT, FPS = 1280, 720, 30
BITRATE = 6_000_000          # ~4 Mbps
INTRA = 30                   # IDR every ~1s @30fps (try 15 for 0.5s)
MTU = 1200

GST = shutil.which("gst-launch-1.0") or "gst-launch-1.0"
RPICAM = shutil.which("rpicam-vid") or "rpicam-vid"

rpicam = (
    f'{RPICAM} -t 0 --width {WIDTH} --height {HEIGHT} --framerate {FPS} '
    f'--codec h264 --profile high --level 4.1 '
    f'--inline --intra {INTRA} --bitrate {BITRATE} --flush --nopreview -o -'
)

gst = (
    f'{GST} -q fdsrc '
    f'! h264parse config-interval=-1 disable-passthrough=true '
    f'! rtph264pay pt=96 mtu={MTU} '
    f'! udpsink host={LAPTOP_IP} port={PORT} sync=false async=false'
)

cmd = f"{rpicam} | {gst}"
print("▶ Starting headless Pi sender:")
print(" ", cmd)

def main():
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    def stop(*_): 
        try: proc.terminate()
        except: pass
        sys.exit(0)
    signal.signal(signal.SIGINT, stop)
    for line in proc.stdout:
        if line.strip(): print(line.strip())
    sys.exit(proc.wait() or 0)

if __name__ == "__main__":
    main()
