#!/usr/bin/env python3
# laptop_print.py — ultra-simple UDP ping/print node for the laptop

import socket, threading, time

# ---- CONFIG (edit these) ----
NAME = "LAPTOP"
LOCAL_PORT = 6001                   # Laptop listens here
PEER_IP = "192.168.137.216"          # <-- your Pi's IP (check with `hostname -I` on the Pi)
PEER_PORT = 6000                    # send to the Pi's listening port
SEND_INTERVAL = 0.5                 # seconds
# -----------------------------

def recv_loop(sock):
    while True:
        data, addr = sock.recvfrom(2048)
        try:
            text = data.decode("utf-8", errors="replace")
        except:
            text = repr(data)
        print(f"[{NAME}] RECV from {addr}: {text}")

def send_loop(sock):
    n = 0
    while True:
        n += 1
        msg = f"{NAME} hello #{n} @ {time.time():.3f}"
        sock.sendto(msg.encode("utf-8"), (PEER_IP, PEER_PORT))
        print(f"[{NAME}] SENT -> {PEER_IP}:{PEER_PORT}: {msg}")
        time.sleep(SEND_INTERVAL)

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", LOCAL_PORT))
    print(f"[{NAME}] Listening on 0.0.0.0:{LOCAL_PORT}")

    threading.Thread(target=recv_loop, args=(sock,), daemon=True).start()
    send_loop(sock)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Laptop] Bye")
