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


**1. Onboard Raspberry Pi (`gs_stream.py`)**

| Parameter | Modify Notes | Matching Script | Matching Script Variable |
|------------|--------------|-------|-------|
| `SERVER_IP` | Replace with the static IP of your server. | *(N/A)* | *(N/A)* |
| `UDP_PORT` | Port used to send the video stream to the server. | `gs_relay_stream.py` | `PORT` |

---

**2. Onboard Raspberry Pi (`controls_receiver.py`)**

| Parameter | Modify Notes | Matching Script | Matching Script Port Variable |
|------------|--------------|-----------------|-------------------------------|
| `STATUS_UDP_PORT` | Port used by the Pi to send status updates to the **server**. | `control_relay.py` | `STATUS_IN_PORT` |
| `UDP_IP` | The Pi’s own local IP address (used internally). Usually `"0.0.0.0"` to listen on all interfaces — no change needed. | *(N/A)* | *(N/A)* |
| `UDP_PORT` | Port where the Pi listens for **control packets** from the server relay. | `control_relay.py` | `PI_CONTROL_PORT` |

---

**3. Control Laptop (`gui.py`)**

| Parameter | Modify Notes | Matching Script | Matching Script Port Variable |
|------------|--------------|-------|-------|
| `HOME_URL` | URL of the WebRTC stream hosted by the server. | `gs_relay_stream.py` | `http://SERVER_IP:WEB_PORT` |
| `PI_IP` | Replace with SERVER_IP and point to static server ip. | *(N/A)* | *(N/A)* |
| `STATUS_PORT` | Port for receiving rover status messages. | `control_relay.py` | `STATUS_OUT_PORT` |
| `CLIENT_CONTROL_PORT` | UDP port on the server that accepts control packets from clients (GUI). | `control_relay.py` | `CLIENT_CONTROL_PORT` |

---

**4. Server (`gs_relay_stream.py`)**

| Parameter | Modify Notes | Matching Script | Matching Script Port Variable |
|------------|--------------|-------|-------|
| `HOTSPOT_IP` | IP of the server’s network interface receiving the Pi’s UDP stream. | *(N/A)* | *(N/A)* | 
| `PORT` | UDP port the server listens on. | `gs_stream.py` | `UDP_PORT` |
| `WEB_DIR` | Directory containing `index.html` for WebRTC streaming. | *(N/A)* | *(N/A)* | 
| `WEB_PORT` | HTTP port for hosting the WebRTC viewer page. | *(N/A)* | *(N/A)* |
| `SIG_PORT` | WebSocket signalling port for WebRTC. | *(N/A)* | *(N/A)* |

---

**5. Additional Server Script (`control_relay.py`)**

!!! warning "Additional control_relay Script Required"
    The `controls_receiver.py` script is **not included by default** and must be **created manually** using the parameter information below.  
    
    The table provides the required configuration values and shows how they link with the server’s `control_relay.py` ports and roles.

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
    - Sends status or acknowledgement packets back through the same relay.

    Once configured, this allows the **server** to act as the sole bridge for both **video** and **control data**, enabling safe and scalable remote teleoperation.

| Parameter | Modify Notes | Matching Script | Matching Script Port Variable |
|------------|--------------|-------|-------|
| `CLIENT_CONTROL_PORT` | Port where the server receives control from GUI. | `gui.py` | `CLIENT_CONTROL_PORT` |
| `PI_CONTROL_IP` | Pi’s IP on the server’s LAN/subnet. The only place that knows the Pi’s IP. | *(N/A)* | *(N/A)* |
| `PI_CONTROL_PORT` | Port where the Pi’s control receiver listens. | `controls_receiver.py` | `UDP_PORT` |
| `STATUS_IN_PORT` | Port where the server receives status from the Pi. | `controls_receiver.py` | `STATUS_UDP_PORT` |
| `STATUS_OUT_PORT` | Port where server relays status to GUI. | `gui.py` | `STATUS_PORT` |




