# Safety Manual  
**ECE4191 – Integrated Design Robotics Project**  
**Team R15 | Mobile Wildlife Monitoring Platform**

---

## 1. Purpose and Scope TEST
This Safety Manual defines safe operating procedures, personal protective equipment (PPE), and emergency response requirements for the **R15 Mobile Wildlife Monitoring Platform**.  
It complements the [Operator Manual](operation.md)  and must be read **before any assembly, testing, or operation** of the system.

The manual applies to all team members during:
- System assembly and testing  
- Operation within the arena  
- Field or lab demonstrations  
- Transport and storage of the unit  

---

## 2. System Overview
The R15 system is a **tele-operated tracked robot** designed for non-invasive wildlife monitoring.

**Subsystems include:**
- **Mobile Base:** Dual tracked chassis driven by two DC motors.  
- **Control Module:** Raspberry Pi Zero 2 W managing navigation, communication, and motion control.  
- **Vision Subsystem:** Panning/Tilting camera with IR illumination for low-light operation.  
- **Operator Interface:** GUI for real-time control, live video feed, and system feedback.  

> **Power behaviour:** The robot’s power supply energises automatically when plugged into mains. There is **no manual power switch**. Treat all power rails as live immediately upon connection.

Refer to: `Operator Manual §2.0 – System Description`

---

## 3. Identified Hazards and Controls

| Hazard Type | Description | Control / Mitigation | Cross-Reference |
|--------------|-------------|----------------------|----------------|
| **Electrical** | Power supply energises instantly on connection, exposing live 12 V and 5 V rails. | Plug in only after verifying all connections are secure. Keep hands clear of exposed terminals. Disconnect from mains before handling. | Operator Manual §3.1 |
| **Thermal** | Motor driver may warm under sustained load. | Ensure ventilation around control board; do not obstruct air gaps. | Operator Manual §3.2 |
| **Mechanical** | Pinch injury from moving treads or servo mechanisms. | Keep hands clear when powered; elevate chassis during testing. | Operator Manual §4.1 |
| **Software / Control** | Unintended motion due to code or network fault. | Software E-Stop; onboard safe-stop logic (≤ 100 ms). | Operator Manual §5.3 |
| **Environmental** | Slips or cable entanglement during tethered operation. | Manage tether with loops and maintain a clear, dry work area. | Operator Manual §6.1 |

---

## 4. Personal Protective Equipment (PPE)

| Activity | Required PPE |
|-----------|--------------|
| Electrical assembly / soldering | Safety glasses, heat-resistant gloves |
| Mechanical assembly | Safety glasses, cut-resistant gloves |
| Testing / operation | Closed-toe shoes, long pants |
| Field operation | High-visibility vest, sun protection |

---

## 5. Standard Operating Procedure (SOP)

### Pre-Operation
1. **Do not plug in the power supply yet.**  
   Inspect the system visually first.  
2. Complete the **Pre-Use Safety Checklist** below.  
3. Verify all connectors are locked, polarity correct, and strain-relieved.  
4. Confirm controller laptop and robot are on the same Wi-Fi network.  
5. Once all checks are complete, **plug in the power supply** to energise the system.  

### Operation
1. Once power is connected, wait for the Raspberry Pi boot sequence (≈ 20 s).  
2. Open the GUI and confirm control responsiveness (motion and camera feed).  
3. Conduct a short (≤ 1 m) motion test before arena entry.  
4. Maintain a **1 m exclusion zone** around the robot during motion.  
5. Use **E-Stop** immediately if movement becomes unsafe or erratic.  

### Shutdown
1. Stop the robot and ensure motors are idle.  
2. Use GUI “Power Down” command if available, or safely disconnect Wi-Fi.  
3. **Unplug the power supply from mains** to remove all power (no switch).  
4. Allow components to cool before handling.  

---

## 6. Pre-Use Safety Checklist

Before every operation, ensure **all items below are completed and verified**.

- [ ] Power supply unplugged during setup  
- [ ] All connectors secure; polarity correct  
- [ ] Power cables intact, no exposed wire  
- [ ] Motors respond evenly to jog commands  
- [ ] Camera tilt range −30° → +90° verified  
- [ ] Software E-Stop halts motors ≤ 0.1 s from activation  
- [ ] GUI displays live video feed  
- [ ] Work area clear of liquids, trip hazards, and tether slack  

---

## 7. Emergency Procedures

| Event | Immediate Action | Follow-Up |
|--------|------------------|-----------|
| **Electrical shock** | Unplug power supply immediately; do not touch victim; call **000** | Report to supervisor and complete incident report |
| **Fire or smoke** | Activate E-Stop; unplug supply; use CO₂ extinguisher | Notify staff; document incident |
| **Mechanical entrapment** | Press E-Stop; manually release if safe | Inspect system before re-energising |
| **Software freeze / runaway** | Use GUI kill command or disconnect tether | Review software behaviour before next use |
| **Trip or tether entanglement** | Halt robot; unplug supply if needed; secure tether loops | Review tether routing protocol |

---

## 8. Training and Authorisation
Only authorised operators may power or control the R15 system.  
Operators must:
- Read this Safety Manual and the [Operator Manual](operation.md)  
- Complete a supervised pre-use demonstration  
---

## 9. Cross-Reference Summary

| Topic | Linked Document / Section |
|--------|---------------------------|
| Power & wiring procedure | Operator Manual §3.1 |
| GUI setup & control | Operator Manual §4.0 |
| Motor & servo testing | Operator Manual §4.2 |
| Communication / latency check | Proposal FU0.1.1 – FU0.2.2 |
| Risk matrix | Proposal §6.c (R1.0 – R3.7) |
| E-Stop compliance | Proposal FU1.2.4 – Software Emergency Stop System |

---

