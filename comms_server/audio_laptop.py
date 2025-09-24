import socket
import struct
import numpy as np
import sounddevice as sd

# ===== Config =====
HOST = "0.0.0.0" 
PORT = 50007
SAMPLE_RATE = 48000         # must match server
CHANNELS = 1
BLOCKSIZE = 16
# ==================

# This script creates a socket on the laptop,
# and then listens to anything coming into the
# port (which is what the pi connects and sends to)

def main():

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)

    print(f"[Server] Listening on {HOST}:{PORT} ...")
    
    conn, addr = s.accept()

    print(f"[Server] Client connected from {addr}")

    with sd.OutputStream(samplerate=SAMPLE_RATE,
                            channels=CHANNELS,
                            dtype='int16',
                            blocksize=BLOCKSIZE) as stream:
        try:
            while True:
                # First read 4-byte length header
                header = b''
                while len(header) < 4:
                    chunk = conn.recv(4 - len(header))
                    if not chunk:
                        print("[Client] Server disconnected")
                        return
                    header += chunk
                (length,) = struct.unpack("!I", header)

                # Then read 'length' bytes of audio
                audio_data = b''
                while len(audio_data) < length:
                    chunk = conn.recv(length - len(audio_data))
                    if not chunk:
                        print("[Client] Server disconnected")
                        return
                    audio_data += chunk

                # Convert bytes back to int16 numpy array
                pcm = np.frombuffer(audio_data, dtype=np.int16)

                # Play audio
                stream.write(pcm)
        except KeyboardInterrupt:
            print("\n[Server] shutting down")

if __name__ == "__main__":
    main()