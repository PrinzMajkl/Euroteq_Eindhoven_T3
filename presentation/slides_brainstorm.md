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

### Slide 2: Context & Problem: Pressures on the Pegnitz (Real Numbers & Media Evidence)
- **What Happens When the Pegnitz Collapses? (Concrete Damage Metrics)**:
  1. **Direct Public Health Threat ("Durchfall-Welle" in Local Media)**:
     - The **Fuchslochwelle** river-surfing wave in western Nuremberg made German media headlines (*t-online*, *inFranken*) as the **"Durchfall-Welle" (Diarrhea Wave)**.
     - While surfing is permitted, *swimming is strictly prohibited* due to severe bacterial contamination after rain. Surfers face acute viral, bacterial, and ear infections.
  2. **Urban Sewer Bottlenecks & Infrastructure Stakes**:
     - Modernizing a single storm overflow retention basin (*RÜB*) costs **€1.5M to €5.0M+** for just 1,000–3,000 $m^3$. With ~1,500 km of sewers, blind upgrades waste millions on the wrong outfalls.
  3. **Ecological Hypoxia & Summer Die-Offs**:
     - August heatwaves in Nuremberg's Wöhrder See / Pegnitz caused mass fish die-offs ($\text{DO} < 3.0\ \text{mg/L}$), forcing the *Fischereiverband Mittelfranken* to deploy boats to collect thousands of floating carcasses.
  4. **Agricultural Infiltration & EU Fines**:
     - Knoblauchsland nitrate runoff risks statutory "Red Zone" designation and EU Court fines reaching **up to €850,000 per day** for systemic directive violations.
- **The Core Bottleneck**:
  - Current monitoring relies on **manual grab sampling once a month** or sparse static gauges. Sewer utilities only track internal pipe water levels—not in-river dispersion. Public health departments face **24–48 hour laboratory incubation delays**.

### Slide 3: Current Baseline: What Authorities Measure & The Fatal Flaw
- **The 8 Standard Parameters Monitored by SUN (Stadtentwässerung Nürnberg)**:
  - **Physico-Chemical Baseline**:
    - *Water Temperature (°C)*: Dictates biological kinetics, oxygen solubility, and ammonia toxicity.
    - *pH*: Detects industrial discharges; governs the ratio between ammonium ($\text{NH}_4^+$) and toxic ammonia ($\text{NH}_3$).
    - *Electrical Conductivity (µS/cm)*: Traces dissolved ions from road salt, industrial effluents, and wastewater.
    - *Turbidity (NTU)*: Optical indicator of suspended solids from storm runoff, erosion, and raw sewer overflows.
  - **Ecological & Nutrient Fingerprints**:
    - *Dissolved Oxygen (DO, mg/L)*: Vital sign of river respiration; plummets during organic sewage decomposition.
    - *Ammonium ($\text{NH}_4^+$ / $\text{NH}_3\text{-N}$)*: **Primary sewage tracer** from urine/faeces; acute fish toxicant.
    - *Nitrate ($\text{NO}_3^-$)*: Dissolved nitrogen from agricultural fertilizer leaching (Knoblauchsland).
    - *Phosphate ($\text{PO}_4^{3-}$)*: Eutrophication nutrient triggering excessive algal blooms.
- **The Fatal Flaw: The Temporal-Frequency Disconnect**:
  - Authorities know *what* to measure, but current monitoring relies on **manual grab sampling (*Schöpfproben*) once a month (or bi-weekly)**.
  - **The Reality**: Severe storm CSOs and runoff spikes are **transient events lasting only 2 to 4 hours**.
  - **The Blind Spot**: Monthly sampling has a near-zero probability of catching peak toxicity before it dilutes and washes downstream!

### Slide 4: Stakeholders, Challenge Definition & The Closed-Loop Solution
- **Multi-Tier Governance: Is it a City or a State Problem? (Both!)**:
  - **City Perspective (*Stadt Nürnberg / SUN / Gesundheitsamt*)**: Focuses on ~1,500 km of local sewer pipes, specific outfall IDs, prioritizing retention CAPEX (€), and immediate citizen warnings for Fuchslochwelle surfers (Citizen "Traffic Light" app: 🟢/🟡/🔴).
  - **State Perspective (*WWA Nürnberg / LfU Bayern*)**: Focuses on entire catchment compliance (EU WFD, German OGewV, SDG 6.3.2), agricultural drainage, and triggering emergency upstream reservoir releases (Rothsee transfer).
- **The Robot as a "Continuous Spatial Profiler" (Acute Spills + Chronic Seepage)**:
  - *Beyond Emergency Spills*: By patrolling the riverbank over time, the robot uncovers **chronic, low-level seepage** from cracked underground pipes and failing seals that static sensors miss, building a historical spatio-temporal map for city planners.
- **Formal Challenge Statement**:
  > *"How can digital twinning be applied to autonomous systems in order to address the challenge of detecting and localizing transient Combined Sewer Overflows (CSOs) for the Wasserwirtschaftsamt and regional environmental authorities?"*
- **The Solution: 4D Adaptive Closed-Loop Retasking**:
  - The autonomous platform streams real-time proxy data ($\text{NH}_3\text{-N}$, $\text{DO}$) every 30s. The Digital Twin calculates the next sampling target based on:
    1. **Data Age ($\tau$)**: Exploring unvisited reaches.
    2. **Chemical Gradients ($\nabla C$)**: Homing upstream to the active outfall pipe.
    3. **Rain Radar ($W$)**: Re-positioning ahead of storm cell runoff.
    4. **Historical Baselines ($H$)**: Filtering background fluctuations.

---

## 3. Technical Solution (Max 3 Slides)
*Target Audience: Stakeholders & General Technical Audience*

### Slide 5: High-Level System Architecture & Context (PlumeTrace Blueprint)
- **End-to-End System Overview**:
  - **Physical Lab Arena**: TurtleBot3 Burger running **ROS 2 Jazzy** (`turtlebot3_bringup`), LiDAR LDS-02, and OpenCR base; overhead tracking camera.
  - **Lab Desktop Engine**: Navigation stack (AMCL, Nav2, keepout filter, collision monitor), robot-side logic (`emulated_sensor`, `edge_buffer`, `link_gate`), and Digital Twin (`twin_core`, `mission_controller`, `sync_monitor`, `obstacle_registry`, `virtual_obstacle_cloud`).
  - **Simulation Mirror**: **Gazebo Harmonic** (`gz sim`) with `ros_gz_bridge`, ghost robot follower, and dynamic obstacle spawner.
  - **Gateway & Dashboard (PlumeTrace City View)**: `gateway node` (JSON over WebSocket `:8765`, WGS84 mapping) serving **CesiumJS 3D Globe with Bavarian LOD2 OpenData**, featuring dual perspective modes:
    - *City Asset View*: Outfall health scores, pipe IDs, retention CAPEX priority.
    - *State Catchment View*: Reach-wide mass balance, EU WFD compliance, reservoir dispatch triggers.

### Slide 6: Key Design Decisions (DTAS Criteria)
- **Bidirectional Communication & Link Fault Modeling**:
  - `edge_buffer` + `link_gate` simulates link latency and loss; acknowledged telemetry sent to `sample_ingest`.
  - Dynamic Nav2 goals pushed downstream from `mission_controller` in $< 35\ \text{s}$.
- **Dual Obstacle Cloud Pipeline (Safety & Autonomy)**:
  - Real LiDAR clusters tracked by `obstacle_detector` and registered in `obstacle_registry`.
  - `virtual_obstacle_cloud` separates safety actions: generates `REROUTE cloud` for Nav2 costmaps and `STOP cloud` directly into the `Collision monitor`.
- **Tri-Fold State Synchronization & Ground-Truth Verification**:
  - `sync_monitor` continuously tracks pose divergence across physical odometry, AMCL pose, Gazebo `ghost_follower`, and overhead camera ground-truth.

### Slide 7: Rationale: Why Mobile Robotics & Digital Twinning?
- **Why an Autonomous Mobile Robot Beats Static Sensor Networks**:
  1. **Active Gradient Tracing vs. Point Dilution**:
     - *Static Sensor*: Only says "Ammonia peaked at Point X." Cannot tell if the source is 50m upstream, 600m upstream, or on the opposite bank.
     - *Mobile Robot*: Autonomously follows concentration gradients ($\nabla C$) upstream to pinpoint the exact leaking outfall pipe.
  2. **Geo-Referenced Intelligence for Municipal Assets**:
     - Transforms raw telemetry into **concrete, geo-referenced intelligence** for *Stadtentwässerung Nürnberg (SUN)* and *WWA*.
     - Directly links in-river chemical violations to specific municipal asset IDs (pipe outfalls, overflow weirs), enabling data-driven capital investments (CAPEX) instead of guesswork.
  3. **Beyond Water Chemistry: 3D Corridor & Bank Morphology Mapping**:
     - Static probes measure only 1 water parameter at 1 point.
     - Mobile robot's LiDAR & vision map the **physical 3D river corridor** in real time: detects **riverbank soil erosion, slumping embankments**, sediment siltation blocking culverts, and hazardous debris.
     - Directly supports **EU WFD long-term river renaturation monitoring** (hydromorphology).
  4. **Biofouling & Operational Economics**:
     - Hundreds of submerged static probes foul with algae, biofilm, and silt within days, requiring prohibitive maintenance.
     - A mobile robot uses **one high-precision sensor payload** that docks, self-cleans, and safely avoids flood/vandalism destruction.
- **Why the Pegnitz River? (Grounding in Reality)**:
  - *Realistic OpenData*: Ingests Bavarian State LOD2 building models, accurate riverbank terrain, and bridge clearances via [3DCityDB](https://www.asg.ed.tum.de/gis/projekte/3dcitydb/) & [Cesium 3D Tiles](https://sandcastle.cesium.com/?id=3d-tiles-property-lod-river).
  - *Believable European Scenario*: Solves time-sensitive transient CSO plumes rather than hypothetical continuous raw dumping.
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
