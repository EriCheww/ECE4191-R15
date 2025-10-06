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

---

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

---

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
