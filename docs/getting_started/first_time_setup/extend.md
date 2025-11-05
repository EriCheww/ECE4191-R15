# WiFi Extender Setup *(Optional)*

If you choose to use a WiFi extender or portable WiFi router instead of a mobile hotspot, the software setup remains the same. However, you must update the network IP addresses used by the Raspberry Pi and the control laptop.

Previously, when using a mobile hotspot, the **control laptop acted as the host**, and all communication was directed to its local IP address.  
When switching to a WiFi router/extender, the **router becomes the new network host**, and each device (Raspberry Pi, control laptop, and any additional clients) will now receive a **different local IP** from the router.

### What You Need to Adjust
- Update any hard-coded or configuration values that reference:
  - The Raspberry Pi's IP address
  - The control laptop's IP address
  - The host address used for video streaming, WebRTC, or remote control messaging
- Ensure all devices are connected to the same WiFi network (the extender/router).

### Changes Needed 
| Script               | IP Variable That needs to change        | Note                                      | 
|----------------------|-----------------------------------------|-------------------------------------------|
| audio_PIClient.py    | HOST = "192.168.137.1"                  | Need to change to Control Laptop's IP     | 
| gs_stream.py         | LAPTOP_IP = "192.168.137.1"             | Need to change to Control Laptop's IP     |
| gui.py               | PI_IP   = "192.168.137.245"             | Need to change to Raspberry Pi's IP       |
|                      | HOME_URL = "http://192.168.137.1:8080/" | Need to change to Raspberry Pi's IP:PORT  | 
| gs_relay_stream.py   | HOTSPOT_IP = "192.168.137.1"            | Need to change to the router’s gateway IP | 

Once the correct IP addresses are updated in your code or configuration files, operation is the same as before. No other code or hardware changes are required.
