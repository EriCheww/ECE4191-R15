# 🦾 R15 Safety Manual  
**ECE4191 – Integrated Design Robotics Project**  
**Team R15 | Mobile Wildlife Monitoring Platform**

---

## 1. Purpose and Scope
This Safety Manual defines safe operating procedures, personal protective equipment (PPE), and emergency response requirements for the **R15 Mobile Wildlife Monitoring Platform**.  
It complements the [Operator Manual](../docs/operator_manual.md) and must be read **before any assembly, testing, or operation** of the system.

The manual applies to all team members during:
- System assembly and testing
- Operation within the arena
- Field or lab demonstrations
- Transport and storage of the unit

---

## 2. System Overview
The R15 system is a **tele-operated tracked robot** designed for non-invasive wildlife monitoring.

**Subsystems include:**
- **Mobile Base:** Dual tracked chassis driven by two DC motors with local cliff detection.
- **Control Module:** Raspberry Pi Zero 2 W managing navigation, communication, and telemetry.
- **Vision Subsystem:** Tilting camera with IR illumination for low-light operation.
- **Operator Interface:** GUI for real-time control, video, and telemetry display.

Refer to: `Operator Manual §2.0 – System Description`

---

## 3. Identified Hazards and Controls

| Hazard Type | Description | Control / Mitigation | Cross-Reference |
|--------------|-------------|----------------------|----------------|
| **Electrical** | Exposure to 12 V and 5 V rails during wiring or testing | Disconnect power before handling; use insulated tools and verify polarity | Operator Manual §3.1 |
| **Thermal** | UBEC or motor driver may overheat under sustained load | Provide 30 mm ventilation clearance; monitor temperature in GUI | Operator Manual §3.2 |
| **Mechanical** | Pinch injury from moving treads or servo mechanisms | Keep hands clear when powered; elevate chassis during testing | Operator Manual §4.1 |
| **Software / Control** | Unintended motion due to code or network fault | Physical E-Stop; onboard safe-stop logic (≤ 100 ms) | Operator Manual §5.3 |
| **Environmental** | Slips or cable entanglement during tethered operation | Manage tether with loops and Velcro; maintain clear work area | Operator Manual §6.1 |

---

## 4. Personal Protective Equipment (PPE)

| Activity | Required PPE |
|-----------|---------------|
| Electrical assembly or soldering | Safety glasses, heat-resistant gloves |
| Mechanical assembly | Safety glasses, cut-resistant gloves |
| Testing or operation | Closed-toe shoes, long pants |
| Field operation | High-visibility vest, sun protection |

All PPE shall comply with **AS/NZS 2161** (gloves) and **AS/NZS 1337** (eye protection).

---

## 5. Standard Operating Procedure (SOP)

### ⚙️ Pre-Operation
1. Complete the [Pre-Use Checklist](#6-pre-use-safety-checklist).  
2. Inspect all wiring, servo mounts, and treads for damage.  
3. Ensure **power supply is OFF** before connecting the tether.  
4. Verify all connectors are locked and strain-relieved.  
5. Confirm controller laptop and robot are on the same Wi-Fi network.  

### 🧭 Operation
1. Power ON in order: **Supply → Raspberry Pi → GUI.**  
2. Confirm telemetry heartbeat ≥ 1 Hz and video feed ≥ 20 fps.  
3. Conduct a short (≤ 1 m) motion test before arena entry.  
4. Maintain a **1 m exclusion zone** during robot motion.  
5. Use **E-Stop** immediately if motion becomes unsafe or erratic.  
6. Monitor GUI for system temperature, battery voltage, and latency.  

### ⏹ Shutdown
1. Stop robot and ensure motors idle.  
2. Power OFF at **supply end first**, then Pi.  
3. Allow components to cool before handling.  
4. Record test results or incidents in `logs/safety_log.md`.  

---

## 6. Pre-Use Safety Checklist

- [ ] Power cables intact, no exposed wire  
- [ ] UBEC output = 5 V ± 5 % verified  
- [ ] Cliff-detection ultrasonic sensor functional  
- [ ] Motors respond evenly to jog commands  
- [ ] Camera tilt range −30° → +90° verified  
- [ ] E-Stop cuts motor power ≤ 0.5 s  
- [ ] GUI displays live video ≥ 20 fps  
- [ ] No loose fasteners or sharp edges  
- [ ] Work area clear of liquids and trip hazards  

---

## 7. Emergency Procedures

| Event | Immediate Action | Follow-Up |
|--------|------------------|-----------|
| **Electrical shock** | Disconnect power at supply; do not touch victim; call **000** | Report to supervisor and file incident report |
| **Fire or smoke** | Activate E-Stop; cut power; use CO₂ extinguisher | Notify staff; document incident |
| **Mechanical entrapment** | Press E-Stop; manually release if safe | Inspect system before re-energising |
| **Software freeze / runaway** | Use GUI kill command or disconnect tether | Log error in safety report |
| **Trip or tether entanglement** | Halt robot; secure tether loops | Review tether routing protocol |

---

## 8. Maintenance and Inspection

| Frequency | Task |
|------------|------|
| **Before each test** | Check connectors, wiring, servo alignment, and tread condition |
| **Weekly** | Verify UBEC and motor temperatures, check structural fasteners |
| **Monthly / after demo** | Insulation test on all power rails; replace worn treads |
| **As needed** | Reprint damaged 3D parts (> 2 mm cracks) |

All maintenance actions must be logged in `/docs/maintenance_register.md`.

---

## 9. Training and Authorisation
Only authorised operators may power or control the R15 system.  
Operators must:
- Read this Safety Manual and the [Operator Manual](../docs/operator_manual.md)  
- Complete a supervised pre-use demonstration  
- Record authorisation in the team’s training register (`/docs/training_log.md`)

---

## 10. Cross-Reference Summary

| Topic | Linked Document / Section |
|--------|----------------------------|
| Power & wiring procedure | Operator Manual §3.1 |
| GUI setup & control | Operator Manual §4.0 |
| Motor & servo testing | Operator Manual §4.2 |
| Communication / latency check | Proposal FU0.1.1–FU0.2.2 |
| Risk matrix | Proposal §6.c (R1.0–R3.7) |
| E-Stop compliance | Proposal §5 – Legal Compliance |

---

## Appendix A – Maintenance Register (template)

| Date | Performed By | Component | Action Taken | Next Due |
|------|---------------|------------|---------------|----------|
| yyyy-mm-dd | Name | Component name | e.g. Replaced left tread | yyyy-mm-dd |

---

> **Note:** This Safety Manual is version-controlled under `/docs/safety.md`.  
> Edits must be reviewed and approved via pull request by the **Team Captain** or **Safety Officer** before merging into `main`.

