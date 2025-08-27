import socket
import threading

# --- ADD at top ---
HOST = ''          # listen on all interfaces
PORT = 5005

last_key = None

def listen_keys():
    global last_key
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    while True:
        data, _ = sock.recvfrom(1024)
        last_key = data.decode().strip()

listener = threading.Thread(target=listen_keys, daemon=True)
listener.start()

# ---- MAIN LOOP----
ch = last_key
last_key = None
if ch:
    # ... existing keyboard switch/case code ...

