# Team Knowledge Base & Master Q&A

Comprehensive conceptual reference and oral defence preparation guide. Every team member should be fluent in these 24 core questions.

---

## 1. Core Concepts & Mission Fundamentals

### Q1: What problem are we solving?
**Answer**: We address unmonitored point-source water pollution—specifically transient Combined Sewer Overflows (CSOs) and illegal wastewater discharges in urban rivers—by combining an autonomous mobile robot with a real-time predictive Digital Twin to localize sources faster than manual sampling.

### Q2: What do we mean by pollution and a pollution source?
**Answer**: Pollution is harmful material entering a water body that degrades its physical, chemical, or biological condition. A point-source pollution discharge (such as a storm outfall, industrial pipe, or sewer relief valve) introduces acute, localized contaminants directly into the river reach.

### Q3: What is a pollution map vs. a Digital Twin?
**Answer**: 
- A **pollution map** is a static visualization that shows where pollution is and how severe it was at discrete measurement points.
- A **Digital Twin** is a dynamic, active cyber-physical system running alongside the real asset. It ingests live telemetry, maintains state synchronization, simulates physical dispersion, estimates probable source locations (e.g., evaluating candidates A, B, and C), and actively decides *where the robot should navigate next* to gather maximum information.

### Q4: What is a Proof of Concept (PoC) and how does it differ from the full system?
**Answer**: 
- A **PoC** is a scaled demonstration proving the fundamental feasibility of the cyber-physical architecture. We use a **TurtleBot3 Burger** in a dry indoor lab arena with software-emulated water quality sensors and physical landmark markers.
- The **Full Real-World System** envisions a fleet of Autonomous Surface Vessels (ASVs) navigating actual river waterways with wet chemical sensor probes, connected to cloud hydrological engines (gauges, weather radar, SCADA).

### Q5: Why are we using TurtleBot3 instead of an aquatic robot?
**Answer**: TurtleBot3 is the designated hardware platform provided within our EuroTeQ course infrastructure. Operating a terrestrial robot in a dry lab is the accepted academic proxy to validate the complete cyber-physical pipeline (ROS 2 Nav2, CycloneDDS, state sync, mathematical plume inversion, dynamic retasking under real wheel slip and network jitter) without the safety and regulatory barriers of early outdoor aquatic testing.

### Q6: Where does the real robot take samples?
**Answer**: In the full system, an ASV navigates the river or an autonomous rover traverses the accessible riverbank inspection corridor, dipping a multi-parameter probe into the river at designated sampling points. In our indoor PoC, measurements are emulated based on the robot's physical $(x, y)$ coordinate position in the arena.

---

## 2. Water Quality & Regulatory Science

### Q7: Why do we measure Ammonia ($\text{NH}_3\text{-N}$) and Dissolved Oxygen ($\text{DO}$)?
**Answer**:
1. **Ammonia Nitrogen ($\text{NH}_3\text{-N}$)**: A definitive chemical signature of untreated municipal sewage, faecal matter, and nitrogenous agricultural/industrial waste. It is highly toxic to fish ($LC_{50}$ in salmonids/cyprinids) and triggers acute statutory violations under the EU Water Framework Directive and German *Oberflächengewässerverordnung* (OGewV) when exceeding $0.6\ \text{mg/L}$.
2. **Dissolved Oxygen ($\text{DO}$)**: The primary vital sign of aquatic ecosystem health. Bacterial breakdown of organic wastewater rapidly consumes oxygen; acute DO depletion indicates active decomposition and immediate ecological collapse.

### Q8: Who are the stakeholders and why do they care?
**Answer**:
- **Wasserwirtschaftsamt (WWA)** *(Regional Water Management Office)*: Needs rapid notification and automated source localization during storm events to stop acute ecological damage.
- **Bayerisches Landesamt für Umwelt (LfU)** *(State Environmental Agency)*: Requires high-resolution spatio-temporal data to identify unmapped outfalls, calibrate hydrodynamic models, and enforce OGewV standards.
- **Municipal Utilities**: Need actionable incident reports to prioritize sewer network repairs and stormwater retention investments.
- **Downstream Communities & Agriculture**: Benefit from early warnings and cleaner water supplies.

### Q9: Why the Pegnitz River (Nuremberg, Bavaria)?
**Answer**: 
1. **OpenData Availability**: Bavarian public OpenData provides real **LOD2** building models, surveyed riverbank topography, and bridge clearances for **3DCityDB** and **Cesium**.
2. **Believable CSO Dynamics**: Highly regulated European rivers do not suffer from continuous open sewage dumping (like unmanaged global rivers), but from transient storm-driven CSOs that manual grab-sampling almost always misses.
3. **Statutory Alignment**: Governed by strict European (EU WFD) and German (OGewV) chemical limits.

---

## 3. Digital Twin Architecture & Operation

### Q10: What is our comparative baseline?
**Answer**: Our baseline is a **fixed-route patrol**. The robot follows a pre-planned sequence of waypoints without dynamic feedback, sampling blindly at fixed intervals (mirroring traditional scheduled monitoring).

### Q11: How is the Digital Twin superior to the baseline?
**Answer**: The adaptive Digital Twin actively evaluates measurements in real time, computes concentration gradients, eliminates unlikely source candidates, and generates optimized next-sampling waypoints. It finds the active outfall significantly faster and with fewer total samples.

### Q12: What predictions does the Digital Twin make?
**Answer**: Given initial sample readings, the Digital Twin uses a 2D advection-diffusion inverse formulation to predict:
1. The spatial distribution of the plume downstream.
2. The probability likelihood $P(\text{Outfall}_i \mid \text{samples})$ for each candidate outfall (A, B, C).
3. The expected concentration at reachable neighboring candidate points.

### Q13: What simulations does the Digital Twin run?
**Answer**: It forward-simulates hypothetical plumes from each candidate outfall ($A$, $B$, and $C$) using an advection-diffusion solver: *"If Outfall A were active, what concentration profile would appear at the robot's current position?"* It then compares the synthetic forward simulations against actual sensor observations to update candidate probabilities.

### Q14: Can you walk through a concrete example of the closed loop?
**Answer**:
1. The robot starts its corridor patrol with candidates A, B, and C designated along the riverbank.
2. Upon approaching a plume, the mock sensor registers an Ammonia spike ($> 0.6\ \text{mg/L}$).
3. The robot initiates a **Sampling Pause (`DWELL_AND_ANALYZE`)** to halt motion and prevent arena overshoot.
4. The 30-second telemetry batch arrives at the Digital Twin Mediator.
5. The 2D NumPy solver computes candidate likelihoods and finds Candidate B has an 82% match.
6. The Mediator calculates an intercept waypoint directed upstream toward Outfall B and transmits it to Nav2 in $< 35\ \text{s}$.
7. The robot resumes navigation, follows the waypoint upstream, and confirms localization at Marker B.
8. An incident alert is pushed to the simulated authority dashboard in $< 60\ \text{s}$.

### Q15: Does the Digital Twin control the robot's motors directly?
**Answer**: **No.** The Digital Twin decides *where* the robot should go (high-level target waypoint). The onboard **ROS 2 Nav2 stack** handles *how* the robot moves, executing local path planning, obstacle avoidance, and motor commands (`/cmd_vel`). This maintains a strict separation of concerns.

---

## 4. Software Stack & Hardware Integration

### Q16: What technologies are used across the pipeline?
**Answer**:
- **Robot Platform**: TurtleBot3 Burger (Raspberry Pi SBC + OpenCR + 360° LiDAR LDS-02).
- **Communication Middleware**: ROS 2 Humble with **Eclipse CycloneDDS** and dedicated `ROS_DOMAIN_ID`.
- **Navigation & Mapping**: Nav2 (`planner_server`, `controller_server`, `bt_navigator`) + `slam_toolbox`.
- **Water Quality Emulation**: ROS 2 Python node emitting synthetic $\text{NH}_3\text{-N}$ and $\text{DO}$ as a function of physical coordinates $(x, y)$.
- **Digital Twin Engine**: Python backend executing a lightweight 2D NumPy advection-diffusion inverse solver.
- **Geospatial & Visualization Layer**: **3DCityDB** storing Bavarian LOD2 city models and **CesiumJS** rendering the interactive 3D web environment.
- **Mission Logging**: `rosbag2` for full topic recording and SQLite for structured evaluation results.

### Q17: What are 3DCityDB and Cesium doing?
**Answer**:
- [**3DCityDB**](https://www.asg.ed.tum.de/gis/projekte/3dcitydb/): An open-source database schema and software package for storing, managing, and exporting semantic 3D city models (CityGML / CityJSON).
- [**CesiumJS**](https://sandcastle.cesium.com/?id=3d-tiles-property-lod-river): A WebGL virtual globe rendering Bavarian LOD2 3D Tiles, river terrain, real-time robot positions, and plume heatmaps.

### Q18: Are we generating the large 3D map during the mission?
**Answer**: **No.** The 3D geospatial environment is prepared beforehand using official Bavarian LOD2 OpenData and loaded into Cesium. The robot only generates a local 2D costmap/occupancy grid for obstacle avoidance during the mission.

### Q19: Why do we use a lightweight 2D NumPy model instead of full CFD (e.g., OpenFOAM)?
**Answer**: Full Navier-Stokes Computational Fluid Dynamics (CFD) takes hours or days to solve, completely violating our $< 2\ \text{minute}$ real-time closed-loop retasking requirement. A closed-form 2D advection-diffusion NumPy model solves in milliseconds, enabling rapid closed-loop adaptation on edge hardware.

### Q20: What are our target latency and SLA metrics?
**Answer**:
- **Telemetry Batch Period**: 30 seconds.
- **Authority Alert Dispatch**: $< 60$ seconds upon threshold exceedance ($> 0.6\ \text{mg/L}$).
- **Closed-Loop Waypoint Return**: $< 120$ seconds (global river SLA); laboratory turnaround achieves $\approx 33\text{--}35$ seconds.

---

## 5. Robustness, Safety & Fail-Safes

### Q21: What happens if the robot cannot reach the next sampling point?
**Answer**: If a waypoint is blocked by an obstacle or outside the navigable corridor, Nav2 aborts the goal. The Digital Twin Mediator catches the navigation failure, marks that coordinate as unreachable, and recalculates the next-best accessible sampling point.

### Q22: What happens if wireless communication drops?
**Answer**: The robot executes a safe fail-safe routine: it halts motion (`cmd_vel = 0`) or safely loiters, buffering sensor readings locally on the Raspberry Pi SBC. It does not blindly navigate without twin synchronization. Once CycloneDDS connectivity recovers, buffered telemetry is flushed and the mission resumes.

### Q23: What is the Riverbank Accessibility Constraint?
**Answer**: In real-world urban rivers, robots typically only have access to one side of the riverbank (no bridges, steep terrain, or private land). Because wastewater from an opposite-bank outfall mixes downstream, the Digital Twin must mathematically invert the dispersion gradient *using samples gathered exclusively along the accessible bank corridor*.

### Q24: What is our final demonstrable MVP?
**Answer**: A live demonstration showing:
1. TurtleBot3 patrolling the physical lab arena.
2. Ingesting simulated Ammonia readings tied to real coordinates.
3. Detecting an acute spike ($> 0.6\ \text{mg/L}$) and executing a Sampling Pause.
4. The Digital Twin updating outfall candidate probabilities and pushing a new upstream waypoint in $< 35\ \text{s}$.
5. The robot dynamically navigating to the active outfall landmark.
6. The entire mission displayed live on the Cesium 3D LOD2 Pegnitz dashboard.
