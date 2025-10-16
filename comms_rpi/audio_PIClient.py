import sounddevice as sd
import numpy as np
print("sounddevice version:", sd.__version__)
print("numpy version:", np.__version__)
print(sd.query_devices())

import socket, struct, queue, signal, sys


# ===== Config =====
HOST = "192.168.137.1" # enter im laptop ip address
PORT = 50007 # pick any free port >= 1024


SAMPLE_RATE = 48000
CHANNELS = 1
BLOCKSIZE = 2048 # if issues make like 320 same as laptop's script
INPUT_DEVICE = 0 # set to whatever index of Google voiceHAT mic gets printed at start of script
# ==================
audio_q = queue.Queue(maxsize=100)

gain = 50

def audio_callback(indata, frames, time, status):
    # Remove DC offset
    indata = indata - np.mean(indata)

    # Applying gain
    indata = indata * gain

    # Convert float32 [-1,1) to int16 bytes
    pcm = np.clip(indata, -1.0, 0.9999695)
    payload = (pcm * 32767).astype(np.int16).tobytes()
    try:
        audio_q.put_nowait(payload)
    except queue.Full: # drop oldest to keep latency low
        try:
            audio_q.get_nowait()
            audio_q.put_nowait(payload)
        except queue.Empty:
            pass


def main():
    print("script starting")
    print(f"[Pi] Connecting to {HOST}:{PORT}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST,PORT))
    print("[Pi] Connected!")


    def shutdown(*_):
        print("\n[Pi] Shutting down.")
        s.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, shutdown)

    with sd.InputStream( samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", blocksize=BLOCKSIZE, device=INPUT_DEVICE, callback=audio_callback, ):
        try:
            while True:
                data = audio_q.get()
                header = struct.pack("!I", len(data))
                s.sendall(header + data)
        except (BrokenPipeError, ConnectionResetError):
            print("[Pi] Client disconnected.")
            s.close()

if __name__ == "__main__":
    main()
