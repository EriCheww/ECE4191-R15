# Control Laptop Setup
This section describes configuring the control computer used for teleoperation and system management. 

It includes installing the GUI interface, verifying network connectivity with the rover, and preparing optional gamepad input.

## Step 1 — Install GStreamer

GStreamer is required for decoding and displaying the live video stream received from the onboard Raspberry Pi.  
Ensure it is installed before running any control or GUI software.

---

### 🪟 Windows
1. Download the official **GStreamer MSI installer** (Complete edition) from:  
   [https://gstreamer.freedesktop.org/download/](https://gstreamer.freedesktop.org/download/)
2. Run the installer and select **Complete** when prompted.
3. During installation, check **“Add GStreamer to PATH for all users”**.
4. Once finished, verify installation:
   ```bash
   gst-launch-1.0 --version
   ```