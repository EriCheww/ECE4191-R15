import socket, json

PORT = 5051
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("0.0.0.0", PORT))
print(f"Listening for Pi status on UDP {PORT}...")

while True:
    data, addr = s.recvfrom(65535)
    msg = json.loads(data.decode("utf-8"))

    pigpio_ok = msg.get("pi_connected")

    gpio = msg.get("gpio", {})
    arr = []
    for p in range(2, 28):
        entry = gpio.get(str(p), {})
        level = entry.get("level", 0)
        # Normalize: 1 if high, else 0
        arr.append(1 if level == 1 else 0)

    print(f'from {addr[0]} pigpio={pigpio_ok} GPIO={arr}')

