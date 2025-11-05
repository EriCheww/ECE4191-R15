# The UHHHH-OHHHHHH Manual  

## Missing Dependencies
Make sure all required dependencies were installed during the **First Time Setup**.  
If you encounter GStreamer-related errors, verify that **both** installer packages were downloaded and installed, as specified in the setup guide.

---

## Live Stream Not Showing Up
If the GUI loads but the video panel only displays a **white screen**, **Error 404**, or similar message, the issue is most likely caused by the relay script not being able to find the `index.html` file.

- Open `gs_relay_stream.py`
- Confirm that the path to the **`webrtcsink-webui`** folder is correct  
- Update the `WEB_DIR` variable if necessary

---

## GUI Not Launching
If the GUI fails to open at all, this is often caused by **incorrect file paths**, especially when loading the **YOLO model** or project directories.

- Double-check all **directory variables**
- Make sure paths match your actual project folder structure

Refer to:  
**[First Time Setup – Control Laptop](getting_started/first_time_setup/control_laptop.md)** → Step 4 — Editable Code Parameters → *MUST EDIT PARAMETERS*

---

## Motors and Servos Not Responding
If the GUI connects and everything appears functional, but the rover does **not move**, the issue is often due to the `pigpiod` daemon not running correctly.  
This can happen if the Pi was rebooted or if scripts were closed incorrectly.

Restart pigpio:

```bash
sudo systemctl restart pigpiod
```
Then re-run the scripts.