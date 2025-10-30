# Server Setup *(Optional)*

The **Server Setup** is an **optional configuration** used to extend the rover’s communication range and enable **remote teleoperation** over the internet or a wider local network.  

In the standard configuration, the control laptop connects directly to the Raspberry Pi via a local Wi-Fi hotspot or shared network.  

The server introduces an additional **relay layer** through a central communication node.


**Purpose of the Server**

- Acts as a **communication bridge** between the Raspberry Pi and remote control laptops.  
- Enables **multi-client access** — multiple users can connect to the same live feed.  
- Provides **network stability and scalability** for longer-range operation or classroom demonstrations.  
- Handles **WebRTC and UDP relay services** to manage video and control data efficiently.


**Typical Network Flow**

- The **Raspberry Pi** sends encoded video and audio streams to the server using UDP.  
- The **server** (relay node) converts the stream into a WebRTC-compatible feed.  
- The **control laptop** connects to this feed and manages user input through the GUI.

!!! note "Current Implementation"
    In the current configuration, the **control laptop also acts as the server**, running both the GUI (`gui.py`) and the WebRTC relay (`gs_relay_stream.py`) locally. 

    This means the **dedicated server setup can be skipped** unless you are deploying for remote or multi-client operation.  

    The optional server configuration remains available for **future scalability** — allowing multiple laptops or remote users to connect to the same live rover stream.


## Dedicated Server Integration

When introducing a **dedicated server** into your communication network, several code parameters across both the **onboard Raspberry Pi** and the **control laptop** must be updated.  

These ensure that video, control, and status data are correctly routed through the server instead of a direct peer-to-peer link.

---

**Overview**

In the default setup:

The Pi streams video directly to the control laptop’s IP address and the control laptop redistributes it as a **WebRTC stream** accessible by other devices connected directly to the control laptop's Access Point within close range.

With the server setup:

The Pi now sends its encoded video stream to the **server**, which then redistributes it as a **WebRTC stream** accessible by any device that can access the server from any range.

---

## Parameters to Update

The following parameters must be configured for server operation.  
You’ll find these inside the relevant Python scripts on the **Raspberry Pi**, **Server**, and **Control Laptop**.

!!! warning "Additional Control Relay Script Required"
    When using a **dedicated server**, an extra **UDP control relay script** is required to forward control packets between the **control laptop** and the **Raspberry Pi**.  

    In this configuration, the control laptop does not communicate directly with the Pi.

    Instead, all UDP packets (e.g., movement commands, servo controls, and status requests) are first received by the **server**, which then relays them to the Pi’s local IP address.

    This ensures:

    - Only the **server** has direct network access to the Raspberry Pi.
    - The **Pi** is isolated from external clients for improved security and NAT traversal.
    - Multiple control laptops can connect through the same relay channel.

    The relay script typically:

    - Listens on a **control input port** (e.g., `5005`) for UDP packets from clients.  
    - Forwards those packets to the Pi’s **control port** on its local subnet (e.g., `192.168.1.20:5005`).  
    - Optionally sends status or acknowledgement packets back through the same relay.

    Once configured, this allows the **server** to act as the sole bridge for both **video** and **control data**, enabling safe and scalable remote teleoperation.

---

**1. Onboard Raspberry Pi (`gs_stream.py`)**

| Parameter | Description | Example Value | Notes |
|------------|--------------|----------------|-------|
| `SERVER_IP` | IP address of the relay server that will receive the UDP video stream. | `"192.168.1.30"` | Replace with the static IP of your server. |
| `UDP_PORT` | Port used to send the video stream to the server. | `5000` | Must match `PORT` in `gs_relay_stream.py`. |
| `BITRATE` | Video encoding bitrate. | `2000k` | Adjust depending on network speed and latency. |
| `WIDTH`, `HEIGHT`, `FRAMERATE` | Video resolution and frame rate. | `640x480 @ 30fps` | Lower these if streaming over slower links. |

---

**2. Server (`gs_relay_stream.py`)**

| Parameter | Description | Example Value | Notes |
|------------|--------------|----------------|-------|
| `HOTSPOT_IP` | IP of the server’s network interface receiving the Pi’s UDP stream. | `"192.168.1.30"` | Must match `SERVER_IP` set on the Pi. |
| `PORT` | UDP port the server listens on. | `5000` | Must match the Pi’s output port. |
| `WEB_DIR` | Directory containing `index.html` for WebRTC streaming. | `"/home/server/ECE4191-R15/webrtcsink-webui"` | Update if the repository is in a different path. |
| `WEB_PORT` | HTTP port for hosting the WebRTC viewer page. | `8080` | Optional — change if this port is already used. |
| `SIG_PORT` | WebSocket signalling port for WebRTC. | `8443` | Only change if needed. |

---

**3. Control Laptop (`gui.py`)**

| Parameter | Description | Example Value | Notes |
|------------|--------------|----------------|-------|
| `HOME_URL` | URL of the WebRTC stream hosted by the server. | `"http://192.168.1.30:8080"` | Must match `WEB_PORT` and server IP. |
| `PI_IP` | IP of the Raspberry Pi for control commands (unchanged). | `"192.168.1.20"` | Still points to the Pi, since commands are sent directly. |
| `STATUS_PORT` | Port for receiving rover status messages. | `5051` | Must match the onboard script configuration. |
| `HOTSPOT_IP` | Server IP (if GUI needs to query or ping it). | `"192.168.1.30"` | Optional — for advanced diagnostics or multi-user mode. |

---


