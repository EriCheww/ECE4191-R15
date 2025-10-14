import subprocess
import time

SSID = "LAPTOP-NU5QD8K3 2616"
PASSWORD = "password123"

def connect_wifi(ssid, password):
    """Try to connect to Wi-Fi. Return True if successful, False otherwise."""
    subprocess.run(
        ["nmcli", "dev", "wifi", "connect", ssid, "password", password],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Check if connected
    result = subprocess.run(
        ["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
        capture_output=True, text=True
    )
    return f"yes:{ssid}" in result.stdout

def run_scripts():
    print("Running script1...")
    subprocess.run(["python3", "/home/user/Desktop/ECE4191/gs_stream.py"])
    print("Running script2...")
    subprocess.run(["python3", "/home/user/Desktop/ECE4191/udp_comms.py"])

if __name__ == "__main__":
    print(f"Trying to connect to Wi-Fi: {SSID}")
    while True:
        if connect_wifi(SSID, PASSWORD):
            print(f"✅ Connected to {SSID}")
            break
        else:
            print("❌ Not connected yet, retrying in 5 seconds...")
            time.sleep(5)

    run_scripts()