# Presentation Brainstorming & Slide Builder

This document contains the slide-by-slide outline, talking points, and brainstorming notes for the final defence presentation.

> [!NOTE]
> Detailed defence rubric, criteria, and audience guidance are documented in [presentation_requirements.md](../general_information/presentation_requirements.md).
> Comprehensive technical specs are in [technical_specifications.md](../general_information/technical_specifications.md) and [project_overview.md](../general_information/project_overview.md).

---

## 1. Title Slide (Max 1 Slide)
*Target Audience: General*

### Slide 1: Project Title & Team
- **Project Title**: Autonomous Closed-Loop Digital Twin for River Pollution Tracking
- **Subtitle**: Detecting and Localizing Transient Combined Sewer Overflows (CSOs) in the Pegnitz River
- **Team Name**: EuroTeQ Eindhoven - Track 3 (T3)
- **Contributing Members**: [Member Names & Affiliations]
- **Key Visuals**: Split render showing the physical TurtleBot3 platform alongside the Cesium/3DCityDB digital twin overlay of the Pegnitz riverbank.

---

## 2. Context and Challenge (Max 3 Slides)
*Target Audience: Stakeholders*

### Slide 2: SDG Context & The Hidden CSO Problem (The "Pegnitz Strategy")
- **Relevant SDG & Regulatory Frameworks**: 
  - **UN SDG 6.3 & Indicator 6.3.2**: Ambient surface water quality protection.
  - **EU Water Framework Directive (WFD / 2000/60/EC)**: Mandate for good ecological status.
  - **German Oberflächengewässerverordnung (OGewV)**: Strict statutory thresholds for toxic pollutants.
- **The Core Problem: Transient Combined Sewer Overflows (CSOs)**: 
  - Unlike unmanaged global rivers with continuous raw dumping, European rivers suffer primarily from acute, storm-driven CSOs.
  - Traditional monitoring relies on manual "grab sampling" (weekly/monthly), which almost completely misses short-lived, transient discharge events before they dissipate.
- **Ecological Urgency**: 
  - Acute Ammonia ($\text{NH}_3\text{-N}$) spike ($> 0.6\ \text{mg/L}$) triggers statutory violation; toxic to fish species and causes rapid Dissolved Oxygen ($\text{DO}$) depletion.

### Slide 3: Stakeholders & Needs
- **Primary Stakeholders**:
  - **Wasserwirtschaftsamt (WWA) Nuremberg**: Needs immediate incident alerts and automated localization of unmapped or illegal CSO outfalls.
  - **Bayerisches Landesamt für Umwelt (LfU)**: Needs continuous, spatio-temporal water data during storm events to update risk maps and enforce OGewV regulations.
  - **Local Municipal Utilities**: Require actionable incident intelligence to prioritize sewer maintenance and stormwater retention.
- **Stakeholder Pain Points**:
  - Static sensor stations cannot localize unmapped outfalls.
  - Manual sampling is slow, reactive, and geographically sparse.
  - Lack of real-time, closed-loop telemetry between field assets and environmental models.

### Slide 4: Challenge Definition
- **Formal Challenge Statement**:
  > *"How can digital twinning be applied to autonomous systems in order to address the challenge of detecting and localizing transient Combined Sewer Overflows (CSOs) for the Wasserwirtschaftsamt and regional environmental authorities?"*
- **Success Criteria**:
  - Detect chemical spikes ($\text{NH}_3\text{-N} > 0.6\ \text{mg/L}$) in real time.
  - Predict upstream source coordinates in under 2 minutes.
  - Dynamically retask the autonomous vehicle to home in on the physical outfall faster and with fewer samples than fixed-route sampling.

---

## 3. Technical Solution (Max 3 Slides)
*Target Audience: Stakeholders & General Technical Audience*

### Slide 5: High-Level System Architecture & Context (PlumeTrace Blueprint)
- **End-to-End System Overview**:
  - **Physical Lab Arena**: TurtleBot3 Burger running **ROS 2 Jazzy** (`turtlebot3_bringup`), LiDAR LDS-02, and OpenCR base; overhead tracking camera.
  - **Lab Desktop Engine**: Navigation stack (AMCL, Nav2, keepout filter, collision monitor), robot-side logic (`emulated_sensor`, `edge_buffer`, `link_gate`), and Digital Twin (`twin_core`, `mission_controller`, `sync_monitor`, `obstacle_registry`, `virtual_obstacle_cloud`).
  - **Simulation Mirror**: **Gazebo Harmonic** (`gz sim`) with `ros_gz_bridge`, ghost robot follower, and dynamic obstacle spawner.
  - **Gateway & Dashboard**: `gateway node` (JSON over WebSocket `:8765`, WGS84 coordinate mapping) serving **PlumeTrace City View** (CesiumJS 3D globe with Bavarian LOD2 OpenData).

### Slide 6: Key Design Decisions (DTAS Criteria)
- **Bidirectional Communication & Link Fault Modeling**:
  - `edge_buffer` + `link_gate` simulates link latency and loss; acknowledged telemetry sent to `sample_ingest`.
  - Dynamic Nav2 goals pushed downstream from `mission_controller` in $< 35\ \text{s}$.
- **Dual Obstacle Cloud Pipeline (Safety & Autonomy)**:
  - Real LiDAR clusters tracked by `obstacle_detector` and registered in `obstacle_registry`.
  - `virtual_obstacle_cloud` separates safety actions: generates `REROUTE cloud` for Nav2 costmaps and `STOP cloud` directly into the `Collision monitor`.
- **Tri-Fold State Synchronization & Ground-Truth Verification**:
  - `sync_monitor` continuously tracks pose divergence across physical odometry, AMCL pose, Gazebo `ghost_follower`, and overhead camera ground-truth.

### Slide 7: Rationale for Digital Twin Approach & The Pegnitz Strategy
- **Why a Digital Twin vs. Alternative Approaches?**:
  - *Vs. Static Sensors*: Fixed probes cannot localize mobile plumes or unmapped outfalls.
  - *Vs. Standalone Autonomous Robot*: Onboard compute cannot run spatial plume inversions or maintain historical LOD2 environmental context.
  - *Vs. Offline Simulation*: A Digital Twin establishes a continuous, bidirectional closed loop—using real-world measurements to update model state, and model inferences to steer physical actions.
- **Why the Pegnitz River? (Grounding in Reality)**:
  - *Realistic OpenData*: Ingests Bavarian State LOD2 building models, accurate riverbank terrain, and bridge clearances via [3DCityDB](https://www.asg.ed.tum.de/gis/projekte/3dcitydb/) & [Cesium 3D Tiles](https://sandcastle.cesium.com/?id=3d-tiles-property-lod-river).
  - *Believable European Scenario*: Solves time-sensitive transient CSO plumes rather than hypothetical continuous raw dumping (contrasting extreme cases like Yamuna River CPCB Class E).
  - *Regulatory Rigor*: Aligns with actual WWA / LfU enforcement thresholds (EU WFD and German OGewV).

---

## 4. Proof of Concept (PoC) (Max 4 Slides)
*Target Audience: Stakeholders & General Technical Audience*

### Slide 8: Solution vs. PoC Delineation (The Course Hardware Proxy)
- **Overall Technical Solution Vision**: Fleet of Autonomous Surface Vessels (ASVs) patrolling real riverways connected to cloud-based multi-tier hydrological twin under UN SDG 6.
- **Academic Context & Course Hardware Constraint**: 
  - Physical experimentation within the course infrastructure utilizes the **TurtleBot3 Burger**.
  - Ground robotics in an indoor dry lab provides an accessible, rapid prototyping environment without the regulatory and physical overhead of deploying aquatic craft.
- **TurtleBot3 as Terrestrial Proxy**:
  - The ground robot acts as a direct cyber-physical proxy for an ASV, validating the complete closed-loop pipeline (telemetry, state sync, 2D plume inversion, and dynamic retasking) under real hardware noise, wheel slip, and wireless network constraints.

### Slide 9: PoC Functional & Non-Functional Scope (DTAS Criteria)
- **Functional Scope Delivered**:
  - Continuous ingestion of `/odom`, `/scan`, and synthetic `/water_quality/ammonia` topics.
  - Autonomous **Sampling Pause (`DWELL_AND_ANALYZE`)** on chemical spike ($> 0.6\ \text{mg/L}\ \text{NH}_3\text{-N}$) to halt forward motion and prevent arena overshoot.
  - Dynamic Nav2 goal generation vectoring the robot upstream to the active outfall candidate.
- **Non-Functional Scope & SLA Targets**:
  - Round-Trip Time (RTT): Real river SLA ceiling $< 120\ \text{s}$; Laboratory turnaround $\approx 33\text{--}35\ \text{s}$ ($30\text{s}$ telemetry cycle + $< 3\text{s}$ NumPy solver).
  - Regulatory Alert Latency: $< 60\ \text{seconds}$ upon threshold breach.
  - Positional Drift Delta: Measured continuously between physical dead-reckoning and Digital Twin coordinates.

### Slide 10: PoC Architecture & Component Pipeline (ROS 2 Jazzy & Gazebo Harmonic)
- **Hardware & Robot Edge Stack**:
  - TurtleBot3 Burger (Raspberry Pi SBC + OpenCR + 360° LiDAR LDS-02) running ROS 2 Jazzy via SSH.
  - `emulated_sensor`: Spatial $\text{NH}_3\text{-N}$ and $\text{DO}$ generation via `reach_frame.yaml`.
  - `edge_buffer` & `link_gate`: Robust store-and-resend queue modeling link loss.
- **Navigation & Safety Stack**:
  - AMCL localization on 2D arena map with Keepout River Filter.
  - Nav2 planner, controller, and behavior trees.
  - `Collision monitor` with real-time `STOP cloud` interception.
- **Digital Twin & Mirror Stack**:
  - `twin_core`: 2D NumPy advection-diffusion solver computing posterior probabilities for Outfalls A, B, and C.
  - `mission_controller`: State machine orchestrating sampling pauses and `NavigateToPose` commands.
  - `sync_monitor`: Cross-referencing AMCL, Gazebo `ghost_follower`, and overhead camera ground-truth.
  - `gateway node` (port `:8765`) streaming to **PlumeTrace City View** (CesiumJS WebGL on port `:8080`).

### Slide 11: Experimental Setup & Comparative Baseline
- **The Comparative Baseline (Control)**:
  - Fixed-route patrol navigating predefined waypoints without real-time feedback (analogous to traditional scheduled monitoring).
- **The Adaptive System (Experimental)**:
  - Dynamic replanning upon detecting plume boundary, discriminating between candidate outfalls.
- **Physical Testbed Setup**:
  - Lab arena corridor with **3 Candidate Outfall Locations (A, B, C)**, where one candidate is active as the simulated effluent emitter during a test run.

---

## 5. Demonstration (Video / Slides)
*Target Audience: Technical Experts (with clear Stakeholder Relevance)*

### Demo Storyboard: Baseline vs. Adaptive Twin
1. **Scene 1: Baseline Patrol (The "Blind" Approach)**
   - TurtleBot executes pre-planned fixed-route navigation.
   - Crosses the pollution plume boundary; sensor logs $> 0.6\ \text{mg/L}\ \text{NH}_3\text{-N}$, but robot blindly drives past without investigating.
2. **Scene 2: Closed-Loop Detection & Sampling Pause (DTAS Evidence)**
   - Adaptive TurtleBot registers $\text{NH}_3\text{-N} > 0.6\ \text{mg/L}$ and initiates **Sampling Pause (`DWELL_AND_ANALYZE`)**.
   - **State Sync**: 30-second telemetry packet received by Digital Twin Mediator; Cesium 3D view displays live robot pose and concentration spike.
3. **Scene 3: Inversion & Environmental Interaction (DTAS Evidence)**
   - Plume Dispersion Engine evaluates probabilities across Candidate Outfalls A, B, and C.
   - Mediator generates updated Nav2 waypoint directed upstream toward the identified active outfall (Candidate B).
4. **Scene 4: Intercept & Source Localization**
   - Robot resumes motion, follows the concentration gradient upstream, and stops directly at Candidate Marker B.
   - Alert broadcast to simulated WWA stakeholder dashboard in $< 60\ \text{s}$.

### DTAS Criteria Verification Checklist
- [x] **Bidirectional Communication**: Continuous telemetry streaming upstream; dynamic Nav2 goal waypoints dispatched downstream.
- [x] **State Synchronisation**: Live physical odometry and chemical readings mapped onto Cesium 3D coordinate frame with drift tracking.
- [x] **Environmental Interaction (Hybrid)**: Physical 360° LiDAR interacting with lab arena obstacles/markers + tight cyber-physical coupling of the synthetic chemical field to physical robot $(x, y)$ coordinates.

---

## 6. Evaluation and Technical Reflection
*Target Audience: Technical Experts*

### Slide 12: Implementation Scope Matrix
| Category | Feature / Capability | Status & Notes |
| :--- | :--- | :--- |
| **Delivered** | TurtleBot3 Gazebo simulation corridor & mapping (`slam_toolbox`) | Fully operational |
| **Delivered** | Synthetic ROS 2 water quality sensor node ($\text{NH}_3\text{-N}$, $\text{DO}$) | Functional with Gaussian spatial field |
| **Delivered** | Fixed-route baseline navigation protocol | Mapped and evaluated |
| **Delivered** | 2D NumPy Advection-Diffusion Plume Engine | Fast analytical implementation |
| **Partially Implemented** | Physical arena bring-up & spatial marker calibration | Transition from Gazebo to lab arena ongoing |
| **Partially Implemented** | Cesium / 3DCityDB integration with Bavarian LOD2 OpenData | Visualization pipeline in progress |
| **Not Implemented** | Full hydrodynamic CFD solver | Intentionally omitted due to $< 2\ \text{min}$ SLA budget |
| **Not Implemented** | Physical aquatic deployment (ASV in real Pegnitz River) | Out of scope for lab PoC |

### Slide 13: Testing, Calibration & Collected Evidence
- **Round-Trip Time (RTT)**: 
  - Achieved telemetry-to-waypoint dispatch latency: *[Insert measured time, e.g., ~45s vs 120s limit]*.
- **Positional Drift**:
  - Measured divergence between physical `/odom` dead-reckoning and Digital Twin coordinates over 10-minute patrol runs.
- **Localization Convergence**:
  - Progression of source identification accuracy across multiple telemetry samples.

### Slide 14: Strengths, Limitations & Risk Reflections
- **Key Strengths**:
  - Validated cyber-physical closed loop under real hardware noise, wheel slip, and wireless DDS conditions.
  - Lightweight mathematical formulation avoids cloud latency bottlenecks ($< 35\ \text{s}$ turnaround).
  - High regulatory relevance directly targeting EU WFD and German OGewV acute pollution criteria.
- **Key Limitations**:
  - **Terrestrial Proxy Platform**: Using the course-provided TurtleBot3 ground robot in a dry indoor arena means aquatic current dynamics, surface wave action, and 3D river depth gradients are not directly modeled physically.
  - Synthetic water quality node relies on spatial coordinate coupling rather than wet chemical sensing probes.
- **Risk Assessment Reflection**:
  - *Network latency on lab Wi-Fi*: Successfully mitigated via CycloneDDS and domain isolation.
  - *Computational delay*: Mitigated by strict avoidance of heavy CFD in favor of 2D NumPy solver.
  - *Sensor drift / odometry slip*: Identified as principal physical barrier requiring spatial recalibration.

### Slide 15: Technical Reflections & Future Opportunities
- **Engineering Insights**:
  - Edge-to-twin data contracts must be lightweight; 30s batching struck the right balance between responsiveness and network congestion.
- **Future Development Opportunities**:
  - Porting navigation stack from ground TurtleBot3 to an Autonomous Surface Vessel (ASV).
  - Ingesting real river sensor feeds from Bavarian LfU monitoring stations.
  - Upgrading 2D dispersion to depth-integrated 2.5D models with seasonal flow dynamics.

---

## Defence Q&A Preparation & Scratchpad
- **Master Oral Defence Guide**: Full 24-point Q&A covering all core concepts, mathematical models, fail-safes, and stakeholder values is documented in [team_knowledge_base.md](../general_information/team_knowledge_base.md).
- **International Benchmark Reference**: See [international_benchmarks.md](../general_information/international_benchmarks.md) for Indian CPCB classes, Kenya standards, and the riverbank accessibility dilemma.
- **Course Gate Execution**: Detailed Gate 1 (Gazebo) & Gate 2 (Lab) setup is in [course_gate_mapping.md](../general_information/course_gate_mapping.md).
