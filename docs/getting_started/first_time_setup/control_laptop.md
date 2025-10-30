# Control Laptop Setup
This section describes configuring the control computer used for teleoperation and system management. 

It includes installing the GUI interface, verifying network connectivity with the rover, and preparing optional gamepad input.

--- 

## Step 1 — Install GStreamer

GStreamer is required for decoding and displaying the live video stream received from the onboard Raspberry Pi.  
Ensure it is installed before running any control or GUI software for your OS, follow the guide on the offical GStreamer website.

1. Download the official **GStreamer MSI installer** (Complete edition) from:  
   [https://gstreamer.freedesktop.org/download/](https://gstreamer.freedesktop.org/download/)
2. Run the installer and select **Complete** when prompted.
3. During installation, check **“Add GStreamer to PATH for all users”**.
4. Once finished, verify installation:
   ```bash
   gst-launch-1.0 --version
   ```

--- 

## Step 2 — Fetching Code from GitHub for Control Laptop

In this step, you will download the control-side software from the GitHub repository.  
The control laptop runs the GUI, network communication, and video/audio receiver code.  
The required files are stored on the **comms_server_dev** branch of the repository.

Use any methond to clone the Repository into your working directory:
   ``` bash 
   git clone -b comms_server_dev https://github.com/EriCheww/ECE4191-R15.git
   ```

--- 

## Step 3 — Downloading Dependencies and Libraries

Once the control-side code has been cloned onto your laptop, the next step is to install all required **dependencies and libraries** that enable the GUI, video streaming, and communication functions.  

This setup ensures that your laptop can:
- Decode and display live **video and audio** streams from the Raspberry Pi.  
- Send **control commands** through a joystick or keyboard to the onboard system.  
- Manage the graphical user interface (GUI) and data visualization tools.  

Both **system-level dependencies** (e.g., GStreamer, PortAudio) and **Python packages** (e.g., OpenCV, Pygame, CustomTkinter) must be installed for proper operation.  

These installations only need to be performed **once**, during the initial setup.

The following sections outline the commands needed to install all dependencies and verify that your environment is ready for operation.

**Core Scripts**

| Script | Purpose | System Dependencies | Python Libraries (Install via `pip`) | Built-in Python Modules |
|---------|----------|--------------------|--------------------------------------|---------------------------|
| **gui.py** | Main GUI for teleoperation, displaying live video feed, alerts, and joystick control. | GStreamer, Tkinter, OpenCV backend | `customtkinter`, `tkwebview`, `Pillow`, `opencv-python`, `numpy`, `pygame` | `time`, `threading`, `queue`, `json`, `re`, `ctypes` |
| **gs_relay_stream.py** | Handles UDP to WebRTC video relay from the Pi to the control system. | **GStreamer (1.20+ full install)**, Python 3.10+ | *(None required)* | `os`, `sys`, `subprocess`, `threading`, `http.server`, `socketserver`, `signal`, `time`, `shutil` |
| **controlls_sender.py** | Reads controller/gamepad input and sends commands to the RPi via UDP. | None | `pygame` | `json`, `socket`, `time`, `threading` |


**Helper Scripts**

| Script | Purpose | System Dependencies | Python Libraries (Install via `pip`) | Built-in Python Modules |
|---------|----------|--------------------|--------------------------------------|---------------------------|
| **alert.py** | Provides pop-up alerts for errors and notifications within the GUI. | None | `customtkinter`, `tkinter` | *(N/A)* |
| **console_window.py** | Displays console logs and runtime messages within the GUI. | None | `customtkinter` | `time`, `threading`, `collections` |
| **advanced_screenshot.py** | Captures annotated screenshots of the video window for debugging or documentation. | Pillow, Tkinter | `Pillow`, `customtkinter` | `os`, `io`, `time` |
| **app_settings.py** | Manages saved user preferences and configuration files. | None | *(None)* | `json`, `pathlib`, `collections`, `threading` |
| **settings_window.py** | Provides settings UI for GUI preferences, screenshot paths, and console limits. | Tkinter | `customtkinter`, `tkinter` | `threading`, `json`, `collections` |
| **screenshot.py** | Captures and saves screenshots of the GUI or video widget area. | Pillow | `Pillow` | `datetime`, `pathlib`, `os` |
| **status.py** | Displays connection and system status indicators within GUI. | None | `customtkinter` | `time`, `threading` |
| **yolo_frame_detector.py** | Detects animals or objects in live video frames using YOLOv8. | None | `ultralytics`, `Pillow` | `time`, `dataclasses`, `typing` |
| **index.html** | Web interface used by the local WebRTC relay server for browser streaming. | WebRTC-capable browser | *(N/A)* | *(N/A)* |


**Quick Install**

Copy and Paste into terminal to install all required Python packages for the Control Laptop.
``` bash
pip install customtkinter tkwebview Pillow opencv-python numpy pygame sounddevice requests ultralytics
```
Or install from the requirements.txt found on the dev branch
```bash 
pip install -r requirements.txt
```

--- 

## Step 4 — Editable Code Parameters
Before running the control laptop software, certain parameters within the scripts must be reviewed and configured.  
These parameters determine how the system connects to the Raspberry Pi, where files are stored, and how the video stream and detection model are accessed.

!!! warning "Critical Configuration Required"
    The following parameters **must be updated before running the program**.  
    If left unchanged, the system may **fail to connect**, **crash at startup**, or **return file not found errors**.

**MUST EDIT PARAMETERS**

| Script | Parameter | Description  | Change Conditions |
|---------|------------|--------------|-------------------------------|
| **gui.py** | `YOLO_MODEL_PATH` | Absolute path to the YOLOv8 detection model. | Parameter must point to the YOLOv8 detection models absolute path! |
| | `PI_IP` | IP address of Raspberry Pi. | Must match your Pi’s assigned address on the network, can be found in Mobile Hotspot! |
| **gs_relay_stream.py** | `WEB_DIR` | Path where `index.html` is served from. | Parameter must point to the folder where index.html is located! |

**Other Parameters**

These parameters are **optional** and can be tuned to match your network, file storage preferences, or custom implementations (e.g., when using a different web server or camera configuration).  
The default values are fully functional for most setups, but advanced users may adjust them for better performance, alternate hardware, or extended communication setups.

!!! note "Server Setup"
    Some of the optional parameters listed below are used when running the **optional server configuration** for extended teleoperation and remote access.  
    These parameters are not required for local operation but will be **explained in detail in the Server Setup** later in this manual.

| Script | Parameter | Description | Default Value | Recommended Change Conditions |
|---------|------------|--------------|----------------|-------------------------------|
| **gui.py** | `HOME_URL` | Default web page or video stream to load (the Pi’s WebRTC viewer). | `"http://192.168.137.1:8080/"` | Change if your WebRTC server runs on a different IP or port. |
| | `SS_SAVE_DIRECTORY` | Local directory for saving screenshots. | `"C:\\ECE4191\\test_photos"` | Update if you want screenshots stored in another folder. |
| | `SS_USER_PREFIX` | Prefix added to saved screenshot filenames. | `'test'` | Modify for user identification or experiment name. |
| | `YOLO_FPS_LIMITER` | Frame-rate cap for object detection. | `10` | Adjust for performance vs. detection frequency. |
| | `STATUS_PORT` | UDP port for receiving status updates from Pi. | `5051` | Change if port conflicts or multiple devices are used. |
| | `PI_PORT` | UDP port for control-signal transmission to Pi. | `5005` | Change only if you modified the Pi’s receiver port. |
| | `PAN_RIGHT_INCREASES`, `TILT_DOWN_INCREASES` | Axis inversion flags for pan/tilt display. | `True` | Flip if camera movement appears reversed. |
| | `send_hz`, `deadzone`, `max_speed` (inside `start_controller_thread`) | Gamepad control parameters. | `20.0`, `0.10`, `100` | Adjust for controller sensitivity and motor response. |
| **gs_relay_stream.py** | `HOTSPOT_IP` | IP of the laptop’s hotspot or network interface. | `"192.168.137.1"` | Change if using a different hotspot IP or LAN. |
| | `WEB_PORT` | HTTP port for the WebRTC viewer page. | `8080` | Modify if port 8080 is already in use. |
| | `SIG_PORT` | WebSocket signalling port for WebRTC. | `8443` | Change only if network conflicts occur. |
| | `PORT` | UDP input port (receives stream from Pi). | `5000` | Must match sender’s port on the Raspberry Pi. |
| | `STREAM_NAME` | Name tag for the WebRTC stream. | `"pi-cam"` | Optional; change to label multiple cameras. |
| | `JITTER_LATENCY_MS` | Buffer latency for smoother streaming. | `5` | Increase slightly if frames drop due to jitter. |
| **controlls_sender.py** | `UDP_IP`, `UDP_PORT` (if present) | Destination IP and port for control packets. | (Typically matches Pi’s `PI_IP:5005`) | Change to align with your Pi network settings. |
| **app_settings.py** | `DEFAULTS` dictionary values (`ss_save_directory`, `ss_user_prefix`, `console_log_length`) | Default paths and log buffer length for the app. | Various defaults (`Screenshots`, `user`, `2000`) | Adjust if you need custom save paths or console size. |
