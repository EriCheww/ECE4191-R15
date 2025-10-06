# Quick Update to know for Tuesdays Testing (7/10/2025)
On the Laptop side: 
ONLY NEED TO RUN gui.py AND gs_relay_stream.py ON THE LAPTOP :D  DONT NEED THE ps4_sender.py ANYMORE !!!
- The gui.py now also contains a thread for ps4_sender.py 
- The previous varibles PI_IP and PI_PORT is now in gui.py
- ps4_sender.py is now renamed to controlls_sender.py found in gui_utils
- Any edits or updates eg for the servo should be done in controlls_sender.py

On the RPi side: 
Updates were made to the PS4_receiver.py and the new copy is called PS4_receiver_status_sender.py 
- PS4_receiver(backup).py works with gui(backup).py in Old Versions (Backups) Folder
- PS4_receiver_status_sender.py  works with gui.py in comms_server Folder


Running Process (Old Verson): 
1. Make sure Mobile Hotspot is connected
2. Run gs_stream.py on RPI
3. Run PS4_receiver.py on RPI
4. Run gs_relay_stream.py on Laptop
5. Run ps4_sender(backup).py in Old Versions (Backup) on Laptop
6. Run gui(backup).py in Old Versions (Backup) on Laptop


Running Process (New Verson): 
1. Make sure Mobile Hotspot is connected
2. Run gs_stream.py on RPI
3. Run PS4_receiver_status_sender.py on RPI
4. Run gs_relay_stream.py on Laptop
5. Run gui.py in comms_server on Laptop


Common Troubleshooting Methods:
1. Make sure Mobile Hotspot connection is active with RPI listed.
2. Make sure variables inside gui.py settings section are correct and pointing to existing folders. Arrows point to most common error casuing hardcoded variables.
```py 
HOME_URL = "http://192.168.137.1:8080/"
# HOME_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ/"           # <------- Comment this out for testing with camera -----------

SS_SAVE_DIRECTORY = "C:\\ECE4191\\test_photos"                                                            # <------------ set random folder is fine ------------
SS_USER_PREFIX = 'test'
YOLO_MODEL_PATH = r"C:\Users\ericl\OneDrive\Documents\GitHub\ECE4191-R15\comms_server\yolo\best.pt"       # <------------ set correct path to the yolo model ------------

YOLO_FPS_LIMITER = 10

MAX_LOG_LINES = 2000  # keep last N lines; adjust as you like
LOG_BUFFER = deque(maxlen=MAX_LOG_LINES)

STATUS_PORT = 5051
PINS = list(range(2,28))

PI_IP   = "192.168.137.144"    # <------------- check pi ip from mobile hotspot window-----------
PI_PORT = 5005                 # <------------- check to make sure same port as code in RPI -----------
```

3. Make sure variables inside gs_relay_stream.py are correct and pointing to existing folders. Arrows point to most common error casuing hardcoded variables.
```py 
# === Paths ===
GST = shutil.which("gst-launch-1.0") or r"C:\Program Files\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe"
WEB_DIR = "C:\\ECE4191\\main_version\\webrtcsink-webui"       # <----------- needs to point to the webrtcsink-webui included in the branch
# WEB_DIR = os.path.join(os.getcwd(), "webrtcsink-webui")
os.makedirs(WEB_DIR, exist_ok=True)
INDEX = os.path.join(WEB_DIR, "index.html")
```

4. Check requirements.txt to make sure no libs are missing.
5. Controller connection may need to be done before running code, connecting during may cause issues. (Untested)

---

# This branch contains all the code the server needs to run for telecommunications. Here's a break down of what each file does.

---

# gs_reciever.py
TLDR: This script is used to check if gstream is working or not. No edits need to be made here for the controller integration.

This script receives RTP (Real-time Transport Protocol) over UDP, carrying H.264 encoded video, and decoding it using hardware. 

To get the stream working, make sure both the RPi and Laptop are on the same network, run the gs_stream.py on the RPi then run gs_reciever.py on the laptop.

When running this script a window would appear with the live camera feed. If no window appear then the gstream is not connecting. 
Common causes: 
- The PORT inside gs_reciever.py is not allowed through the     firewall on the laptop. There is a command line you can copy and paste into Windows Powershell, just ask chat.

- The LAPTOP_IP and PORT inside gs_stream.py on the RPi does not match the laptops IP and PORT. To check your laptop IP type in 'ipconfig' into cmd and look for 'Wireless LAN adapter Local Area Connection* 2: IPv4 Address : 192.168.137.1'

- The RPi and Laptop are not in the same local network (not using mobile hotspot).

How the video is displayed: 
d3d11videosink is GStreamer’s Direct3D 11 video sink on Windows. When the pipeline goes to PLAYING, this element creates a native Win32 window and renders frames to it via Direct3D. If you removed d3d11videosink (e.g., replaced it with fakesink or appsink), no window would appear.

---
# gs_relay_stream.py
TLDR: This script receives, decodes and encodes again for WebRTC. No edits need to be made here for the controller integration.

To get the stream working, make sure both the RPi and Laptop are on the same network, run the gs_stream.py on the RPi then run gs_relay_stream.py on the laptop. 

Now go to any browser and go to http://HOTSPOT_IP:WEB_PORT/, should just be http://192.168.137.1:8080/.

# DO NOT RUN BOTH gs_reciever.py AND gs_relay_stream AT THE SAME TIME, ONLY ONE.

---
# udp_comms_server.py
TLDR: This script handles the communication between RPi and Laptop(Server). Edits need to be made here.

First to get the communications working, make sure both the RPi and Laptop are on the same network, then run the udp_comms.py on the RPi and run udp_comms_server.py on the laptop. You should see messages in the both terminals of communication. 

If not then these are common causes of the error:

- Make sure both the udp_comms_server.py and udp_comms.py both have matching information. Making sure PEER_IP is of the other device and PEER_PORT is set to the other's LOCAL_PORT. This should already be done. 

- The LOCAL_PORT inside udp_comms_server.py is not allowed through the firewall on the laptop. There is a command line you can copy and paste into Windows Powershell, just ask chat.

This is the main function that needs to be edited:
```py 
def send_loop(sock):
    n = 0
    while True:
        n += 1
        msg = f"{NAME} hello #{n} @ {time.time():.3f}"
        sock.sendto(msg.encode("utf-8"), (PEER_IP, PEER_PORT))
        print(f"[{NAME}] SENT -> {PEER_IP}:{PEER_PORT}: {msg}")
        time.sleep(SEND_INTERVAL)
```

This is the message:
```py 
msg = f"{NAME} hello #{n} @ {time.time():.3f}"
``` 

This is how its sent: 
```py 
sock.sendto(msg.encode("utf-8"), (PEER_IP, PEER_PORT))
``` 

The receive_loop inside udp_comms.py on the RPi needs to be edited to convert the message to motor commands.

# For controlls all we need to run are the two udp_comms.py files on the RPi and Laptop, no stream needed.

---

# GUI

Steps to use the GUI: 
1. Both RPi and Laptop connected to Laptops Mobile Hotspot
2. RPi needs to be running the gs_stream.py
3. Check webrtcsink-webui/index.html path and check WEB_DIR variable inside gs_relay_stream.py.
4. Laptop needs to be running the gs_relay_stream.py 
5. Run the gui.py script in a seperate terminal 

For now try pressing w a s d and it should print in the terminal where gui.py is ran. This is just to confirm that the video and commands can be done simultaneously.  
