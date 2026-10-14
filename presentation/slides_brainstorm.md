# Presentation Brainstorming & Master Slide Deck Guide

This document contains the complete, section-by-section slide outline, detailed talking points, technical justifications, and defence arguments for the final EuroTeQ Track 3 defence presentation.

> [!IMPORTANT]
> This structure strictly adheres to the official defence evaluation rubrics documented in [presentation_requirements.md](../general_information/presentation_requirements.md):
> 1. **Section 1**: Title Slide (Max 1 slide)
> 2. **Section 2**: Context and Challenge (Max 3 slides)
> 3. **Section 3**: Technical Solution (Max 3 slides) – *Overarching Real-World Vision*
> 4. **Section 4**: Proof of Concept (PoC) (Max 4 slides) – *Course Hardware Proxy & Laboratory Validation*
> 5. **Section 5**: Demonstration (Video / Slides) – *Core DTAS Evidence*
> 6. **Section 6**: Evaluation and Technical Reflection (Flexible / 4 slides) – *Scope, Calibration, Limitations, Roadmap*

---

## 1. Title Slide (Max 1 Slide)
*Target Audience: General*

### Slide 1: Project Title, Brand & Team
- **Project Title**: **PlumeTrace – Autonomous Digital Twin for River Water Protection**
- **Subtitle**: Detecting, Tracking, and Localizing Transient Combined Sewer Overflows (CSOs) in the Pegnitz River
- **Brand & Theme**:
  - Official Project Logo: [**`assets/logo.jpeg`**](assets/logo.jpeg)
  - Visual Theme: Clean, modern, minimalist white background (`#FFFFFF`) with pure Calibri typography.
  - Palette: Midnight Navy (`#023047`), River Cyan (`#219ebc`), Sky Breeze (`#8ecae6`), Amber Gold (`#ffb703`), Tangerine Alert (`#fb8500`).
- **Institutional Context**: EuroTeQ Engineering University – Track 3 (T3)
- **Contributing Team**: [Team Members & Academic Affiliations]
- **Core Vision Pillars**:
  1. Autonomous River Robotics (Mobile active sensing)
  2. Predictive Cloud Digital Twin (Hydrodynamic simulation & retasking)
  3. AI-Powered Public & Municipal Interfaces (MCP & Open Data access)
- **Presenter Spoken Script (Target: 0:45 min)**:
  > *"Good morning members of the jury and mentors. Today, we present PlumeTrace – an autonomous, closed-loop Digital Twin system designed to protect urban rivers.*
  > *Across Europe, urban rivers are essential for recreation, drinking water, and ecology. Yet beneath the surface, they face sudden, unmonitored pollution events that traditional testing completely misses.*
  > *Using the Pegnitz River in Nuremberg as our testbed, we demonstrate how coupling an autonomous robotic agent with a real-time predictive Digital Twin transforms water quality monitoring from blind, infrequent sampling into actionable protection."*

---

## 2. Context and Challenge (Max 3 Slides)
*Target Audience: Stakeholders (Municipal Authorities, Environmental Regulators, Recreators)*

### Slide 2: Context & Pressures on the Pegnitz (Real Numbers & Media Evidence)
*SDG 6.3 Ambient Water Quality & Real-World Urban Pressures*
- **Four Urgent Pressures Colliding in One Urban Corridor**:
  1. **Direct Public Health Threat ("Durchfall-Welle" in German Media)**:
     - The **Fuchslochwelle** river-surfing wave in western Nuremberg made German media headlines (*t-online*, *inFranken*) as the **"Durchfall-Welle" (Diarrhea Wave)**.
     - While surfing is legally permitted, *swimming is strictly prohibited* due to severe bacterial contamination after rain. Surfers and waders face acute gastrointestinal, viral, ear, and skin infections.
  2. **Urban Sewer Bottlenecks & Multi-Million EUR Infrastructure Stakes**:
     - Modernizing a single storm overflow retention basin (*Regenüberlaufbecken - RÜB*) costs **€1.5M to €5.0M+** for just 1,000–3,000 $m^3$ of capacity.
     - With ~1,500 km of municipal sewer network in Nuremberg, blind capital investment without empirical spatial data risks spending millions on the wrong outfalls.
  3. **Agricultural Infiltration & EU Infringement Penalties**:
     - Intensive vegetable farming in Knoblauchsland causes nitrate ($\text{NO}_3^-$) leaching into alluvial drinking water aquifers.
     - Risks statutory "Red Zone" designation and EU Court fines reaching **up to €850,000 per day** for systemic Water Framework Directive violations.
  4. **Summer Climate Heat & Ecological Hypoxia**:
     - August heatwaves reduce Pegnitz river discharge, concentrating urban effluent and causing dissolved oxygen to collapse below **$3.0\ \text{mg/L}$** (mass fish die-offs requiring municipal emergency collection).
- **Presenter Spoken Script (Target: 1:15 min)**:
  > *"Why the Pegnitz River? Because it represents four urgent pressures colliding in one urban corridor:*
  > *First, Public Health: Surfers at the Fuchslochwelle wave and waders face raw sewage contamination after storms, creating immediate infection risks that made German headlines as the 'Diarrhea Wave'.*
  > *Second, Urban Infrastructure: Nuremberg's 1,500 km sewer network overspills during heavy rains. Modernizing a single retention basin costs between 1.5 and 5 million euros – cities cannot afford to invest blindly.*
  > *Third, Agriculture: Intensive farming in Knoblauchsland leaches nitrates into alluvial drinking aquifers under strict EU penalties.*
  > *And fourth, Climate Drought: Summer heat reduces river discharge, collapsing oxygen levels below 3 mg/L and killing fish."*

### Slide 3: Current Monitoring Baseline & The Fatal Flaw
*The Mismatch Between Measurement Parameters and Temporal Reality*
- **What Authorities Measure: The 8 Standard Parameters (SUN & WWA Nürnberg)**:
  - *Physico-Chemical Baseline*: Temperature (°C), pH, Electrical Conductivity (µS/cm), Turbidity (NTU).
  - *Ecological & Nutrient Tracers*: Dissolved Oxygen (DO, mg/L), **Ammonium ($\text{NH}_4^+$ / $\text{NH}_3\text{-N}$)** – the *primary chemical fingerprint of raw domestic sewage*, Nitrate ($\text{NO}_3^-$), and Phosphate ($\text{PO}_4^{3-}$).
- **The Fatal Flaw: The Sampling Gap**:
  - *Automatic Fixed Probes*: Continuous, but confined to a few sparse monitoring stations. Blind to localized discharges occurring between stations.
  - *Manual Grab Sampling (Schöpfproben)*: Taken only **once a month (or bi-weekly)**; microbiological laboratory cultures require **24 to 48 hours** incubation.
  - *The Reality of Storm Overflows (CSOs)*: Acute convective storm runoff plumes are **transient events lasting only 2 to 4 hours**.
- **Bottom Core Takeaway**:
  - **The Result**: *Plume arrives, causes harm, and clears undetected.* By the time lab results confirm contamination days later, the toxic plume has long dispersed downstream.
- **Presenter Spoken Script (Target: 1:15 min)**:
  > *"To address this, we looked at what municipal authorities currently measure.*
  > *In Nuremberg, the drainage service SUN tracks eight standard parameters: temperature, pH, conductivity, turbidity, dissolved oxygen, and nutrients like ammonium, nitrate, and phosphate. Ammonium is the critical chemical fingerprint of raw sewage.*
  > *The sampling gap is two-fold: automated sensors are confined to a few fixed points, while manual sampling happens as rarely as once a month with days of lab delay.*
  > *The result: acute plumes arrive, cause damage, and clear completely undetected."*

### Slide 4: Key Stakeholders & Challenge Definition
*Framing Current Pain Points and the Formal DTAS Question*
- **Primary Stakeholders: Local Authorities (WWA Nürnberg & SUN)**:
  - *Spatial Blindness*: Fixed river stations cannot distinguish which of dozens of municipal outfall pipes caused a chemical spike.
  - *Blind Infrastructure Investments*: Forced to allocate €1.5M–€5M+ per retention basin based on theoretical pipe models rather than empirical in-river impact.
  - *Chronic Pipe Seepage*: Low-level cracked sewer pipes remain undetected until physical structural collapse.
  - *Regulatory Delay*: Lab culture results arrive 24–48 hours too late for emergency public health action.
- **Secondary Stakeholders: Citizens & Water Sports (Surfers, Waders, Residents)**:
  - *Temporal Blindness*: Zero real-time visibility into river water safety.
  - *Acute Exposure Risk*: Swimmers enter the river during toxic overflow events, causing avoidable bacterial illnesses.
  - *Unusable Data*: Existing municipal water reports are released weeks late and buried in complex chemical tables.
- **Formal Challenge Statement (DTAS Rubric Requirement)**:
  > *"How can digital twinning be applied to autonomous systems in order to address the challenge of detecting and localizing transient Combined Sewer Overflows (CSOs) for the Wasserwirtschaftsamt and regional environmental authorities?"*
- **Presenter Spoken Script (Target: 1:15 min)**:
  > *"This monitoring failure creates acute problems for our two key stakeholder groups today:*
  > *First, Water Authorities like SUN and WWA: They must invest millions of euros into retention basins, but without spatial plume tracking, they are forced to invest blindly without knowing which overflow pipes cause the greatest damage. Furthermore, laboratory delays mean they only learn of acute spills days after they have already washed away.*
  > *Second, Citizens and Surfers: People entering the Pegnitz at the Fuchslochwelle or in city parks have zero real-time warning. They unknowingly expose themselves to acute bacterial contamination because municipal data is either delayed by days or buried in complex chemical reports.*
  > *This frames our formal challenge definition: How can digital twinning be applied to autonomous systems to detect and localize transient Combined Sewer Overflows for environmental authorities?"*

---

## 3. Technical Solution (Max 3 Slides)
*Target Audience: Stakeholders & General Technical Audience*
*Focus: Overarching Long-Term System Vision in the Real World (NOT the lab testbed!)*

### Slide 5: The PlumeTrace Architecture (System Ecosystem)
*The Tri-Tier System: In-River ASV + Cloud Digital Twin + Municipal Command Center*
- **Tier 1: Autonomous River Robot (Aquatic Physical Layer)**:
  - *Platform*: Autonomous Surface Vessel (ASV) – solar/battery-powered catamaran hull designed for urban river currents.
  - *Sensory Payload*:
    - Submersible real-time water quality probe: Ammonium ($\text{NH}_4^+$), Dissolved Oxygen, Electrical Conductivity, Turbidity, pH.
    - Mast-mounted **360° LiDAR**: Scans riverbank morphology, overhanging vegetation, bridge clearances, and unmapped culverts.
    - Downward-looking **Bathymetric Sonar / Echo-Sounder**: Scans the **riverbed (*dno*)**, measuring water depth, sediment accumulation, and siltation blocking outfall mouths.
  - *Edge Autonomy*: Local obstacle avoidance, dynamic waypoint execution, edge telemetry buffer, and automated inductive docking station.
- **Tier 2: Predictive Cloud Digital Twin (Simulation & AI Core)**:
  - *Hydrodynamic Simulation*: 2D/3D advection-dispersion model resolving river velocity vectors, dilution, and plume kinetics.
  - *Real-Time Open Data Assimilation*:
    - **DWD Precipitation Radar**: Live rain cell tracking forecasting surface runoff arrival across urban sub-catchments.
    - **GKD Bayern Gauges**: Live river discharge ($m^3/s$) and upstream water temperatures.
  - *Autonomy Guidance Engine*: Continuously evaluates real-time telemetry against the hydrodynamic model and calculates optimal navigation goals for the robot.
- **Tier 3: Municipal Command Center (Decision & Compliance Layer)**:
  - *3D Geospatial Twin*: Built on **CesiumJS** integrating **Bavarian State LOD2 3D building models and river geometry**.
  - *Actionable Visualization*: Live spatio-temporal pollution heatmaps, outfall asset health scoring, and reach-wide mass balance.
  - *Statutory Dispatch*: Automated alerts sent to WWA and SUN in **$< 60\ \text{seconds}$** upon threshold breach.
- **Presenter Spoken Script (Target: 1:30 min)**:
  > *"Here is our overarching technical solution: PlumeTrace connects physical robotics, cloud digital twinning, and municipal decision-making into one unified ecosystem.*
  > *First, on the water: An Autonomous Surface Vessel continuously patrols the Pegnitz corridor, equipped with chemical sensors for ammonium and dissolved oxygen, 360-degree LiDAR mapping riverbank morphology, and bathymetric sonar scanning the riverbed and sediment build-up.*
  > *Second, in the cloud: A predictive Digital Twin runs hydrodynamic advection-dispersion modeling. By assimilating real-time weather radar from the German Weather Service (DWD) and river discharge, the twin anticipates where storm runoff will arrive and tells the robot where to navigate next.*
  > *Third, in the city hall: A 3D geospatial dashboard built on CesiumJS and Bavarian LOD2 OpenData translates raw data into outfall asset health scores, enabling targeted infrastructure investment and immediate public warnings."*

### Slide 6: Autonomous Closed-Loop Guidance & Digital Twin Rationale
*How the Twin Directs the Robot and Why Digital Twinning is the Superior Paradigm*
- **4D Adaptive Retasking (How the Twin Directs the Robot)**:
  - Rather than driving static patrol paths, the robot's navigation goals are dynamically recomputed based on a 4D objective function:
    1. **Chemical Gradient Homing ($\nabla C$)**: Automatically traces rising ammonium concentrations upstream directly to the discharging pipe.
    2. **Storm Rain Radar Anticipation ($W$)**: Re-positions the vessel downstream of high-risk outfalls *before* runoff arrives in the river.
    3. **Information Freshness ($\tau$)**: Prioritizes unvisited reaches to discover chronic, low-level pipe seepage that static sensors miss.
    4. **Baseline Filtering ($H$)**: Disregards background agricultural fluctuations.
  - Dynamic Nav2 goal updates generated and pushed downstream in **$< 35\ \text{seconds}$**.
- **Digital Twin Rationale: Why Twinning Beats Static Networks**:
  - *Active Tracing vs. Point Dilution*: A static sensor only detects a diluted passing mix; our twin directs the robot upstream to identify the exact outfall.
  - *Predictive vs. Reactive*: Assimilating weather radar forecasts contamination hours ahead of delayed laboratory incubation.
  - *Dual Physical & Chemical Intelligence*: Simultaneously maps water chemistry and 3D riverbed/bank morphology (supporting EU river renaturation).
  - *Operational Economics*: One mobile, self-cleaning robot replaces **50+ submerged static probes** that foul with biofilm, silt, and get destroyed during floods.
- **Presenter Spoken Script (Target: 1:30 min)**:
  > *"The core innovation of PlumeTrace is its Autonomous Closed Loop.*
  > *Instead of driving a static patrol line, our system continuously recomputes waypoints based on a 4D objective function: tracking chemical gradients upstream, anticipating rain runoff via live weather radar, and ensuring older areas are revisited.*
  > *Why does digital twinning beat traditional static sensors? Static probes suffer from point dilution: they tell you pollution passed, but cannot identify where it originated. By coupling physical sensing with predictive twin simulation, we pinpoint the exact leaking outfall in minutes."*

### Slide 7: Stakeholder Action, Open Data & AI Public Access
*Delivering Concrete Value to Municipalities and Everyday Citizens*
- **City & Authority Command (SUN & WWA Nürnberg)**:
  - *Outfall Asset Health Scores*: Links chemical river violations directly to specific municipal pipe asset IDs (e.g., `RÜB-14 Pegnitz West`).
  - *Targeted Infrastructure Investments*: Provides empirical in-river evidence proving which retention basins require expansion (€1.5M–€5M+ CapEx).
  - *Chronic Seepage Localization*: Uncovers cracked underground pipes before structural failure.
  - *Regulatory Audit Trails*: Generates automated compliance logs for the EU Water Framework Directive and German *Oberflächengewässerverordnung* (OGewV).
- **AI-Powered Public Access via Model Context Protocol (MCP)**:
  - *Standardized MCP Integration*: PlumeTrace exposes an MCP server allowing AI assistants (e.g. ChatGPT, Claude, Gemini) to query live Digital Twin state.
  - *Conversational Citizen Queries*:
    - *"Can I surf at the Fuchslochwelle wave this afternoon?"*
    - *"Is the Pegnitz safe for my dog to swim in right now?"*
  - *Actionable Citizen Traffic Light*:
    - 🟢 **Green (Safe)**: Baseline conditions, all recreation safe.
    - 🟡 **Yellow (Caution)**: Marginal post-storm runoff, elevated turbidity.
    - 🔴 **Red (Hazard)**: Active sewage plume detected upstream; high infection risk.
  - *Impact*: Replaces delayed monthly PDFs with instant, transparent public health protection.
- **Presenter Spoken Script (Target: 1:30 min)**:
  > *"Finally, how do stakeholders interact with PlumeTrace?*
  > *For Water Authorities (SUN & WWA): We provide concrete asset intelligence. By assigning health scores to specific outfall IDs, we provide the empirical justification needed to prioritize multi-million euro retention basin expansions.*
  > *For Citizens and Surfers: We expose the Digital Twin via the Model Context Protocol (MCP). Anyone can ask an AI assistant: 'Can I surf at the Fuchslochwelle wave today?' or 'Is the river safe for my dog right now?'. The AI queries live telemetry and forecasts, returning a clear traffic light advisory (Green, Yellow, or Red). This transforms complex environmental chemistry into immediate, transparent public safety."*

---

## 4. Proof of Concept (PoC) (Max 4 Slides)
*Target Audience: Stakeholders & General Technical Audience*
*Focus: Laboratory Implementation, Course Constraints, Hardware Proxy, and Component Pipeline*

### Slide 8: Solution vs. PoC Delineation (The Course Hardware Proxy)
*Honest Delineation Between Long-Term Solution and Course Prototype Scope*
- **Scope Delineation Table**:

| Dimension | Full Technical Solution (Vision) | Laboratory Proof of Concept (Course PoC) |
| :--- | :--- | :--- |
| **Physical Platform** | Autonomous Surface Vessel (ASV Catamaran) | **TurtleBot3 Burger** (Course-mandated ground robot) |
| **Operating Environment** | Real Pegnitz River (Nuremberg urban reach) | **Indoor dry laboratory arena** (Calibrated scaled corridor) |
| **Water Sensing** | Submerged physical ion-selective probes ($\text{NH}_4^+$) | **Emulated spatial chemical sensor node** (`reach_frame.yaml`) |
| **Riverbed / Bank** | 360° LiDAR + Downward Bathymetric Sonar | **LDS-02 2D LiDAR** (Arena perimeter & obstacle boundaries) |
| **Digital Twin Engine** | Cloud hydrodynamic CFD solver + DWD radar | **2D NumPy Advection-Diffusion solver** + live mediator |
| **Visualization** | Production municipal dashboard | **CesiumJS 3D WebGL** with Bavarian LOD2 OpenData |

- **Why TurtleBot3 in a Dry Lab? (Academic Hardware Constraint)**:
  - *Course Infrastructure Mandate*: The TurtleBot3 Burger is the designated, supported robotics platform provided within the EuroTeQ laboratory curriculum.
  - *Cyber-Physical Proxy*: Ground robotics provides an ideal, accessible cyber-physical surrogate for an ASV, validating the complete closed-loop pipeline (telemetry ingest, state synchronization, plume inversion, and dynamic retasking) under **real physical hardware constraints** (wheel slip, odometry drift, motor backlash, and wireless DDS dropouts) without the regulatory hurdles of launching uncertified craft into a public waterway.
- **Presenter Spoken Script (Target: 1:15 min)**:
  > *"Moving to our Proof of Concept: We draw a clear boundary between our overarching full-scale solution and what was validated within the course framework.*
  > *Because the course laboratory infrastructure provides the TurtleBot3 Burger, we utilized this ground robot as a direct terrestrial proxy for an Autonomous Surface Vessel.*
  > *By navigating a calibrated dry arena corridor, the TurtleBot validates the entire cyber-physical closed loop under real physical conditions – real motor noise, wheel slip, and wireless network dropouts – proving that our Digital Twin architecture functions flawlessly on actual embedded hardware."*

### Slide 9: PoC Functional & Non-Functional Scope (DTAS Criteria)
*Mapping Course Implementation to Formal Engineering Requirements*
- **Functional Scope Delivered**:
  - *Continuous Telemetry Ingestion*: Robot streams physical `/odom`, `/scan` (LiDAR), and spatial `/water_quality/ammonia` topics every 30 seconds.
  - *Autonomous Sampling Pause (`DWELL_AND_ANALYZE`)*: Upon crossing the regulatory threshold ($> 0.6\ \text{mg/L}\ \text{NH}_4^+$), the robot automatically halts forward motion to collect a stationary chemical profile, preventing arena overshoot.
  - *Dynamic Nav2 Retasking*: Mediator computes the most probable active outfall and pushes an updated `NavigateToPose` goal back to the robot.
- **Non-Functional SLA Targets & Safety Criteria**:
  - *Round-Trip Time (RTT)*: Real river SLA ceiling $< 120\ \text{s}$; Laboratory target turnaround $\approx 33\text{--}35\ \text{s}$ ($30\text{s}$ telemetry batching + $< 3\text{s}$ analytical NumPy inversion).
  - *Alert Latency*: Regulatory outfall violation broadcast to dashboard in $< 60\ \text{seconds}$.
  - *Dual Obstacle Cloud Pipeline*: Real-time separation of safety actions:
    - `REROUTE cloud`: Dynamically updates Nav2 costmaps for smooth obstacle circumvention.
    - `STOP cloud`: Directly intercepts the robot's `Collision Monitor` for instant emergency stopping.
- **Presenter Spoken Script (Target: 1:15 min)**:
  > *"In our PoC functional scope, we strictly mapped our architecture against DTAS criteria.*
  > *When the TurtleBot crosses a chemical threshold of 0.6 mg/L, it triggers an autonomous Sampling Pause – stopping motion to collect stationary telemetry and prevent overshooting the plume.*
  > *On the non-functional side, we established strict SLA targets: an emergency alert latency under 60 seconds, and a closed-loop turnaround of 35 seconds.*
  > *Furthermore, our dual-zone obstacle pipeline separates smooth costmap rerouting from emergency collision stops, ensuring total physical safety."*

### Slide 10: PoC Architecture & Component Pipeline (ROS 2 Jazzy & Gazebo)
*Detailed Technical Implementation of the Cyber-Physical Stack*
- **Hardware & Robot Edge Stack**:
  - *Platform*: TurtleBot3 Burger with Raspberry Pi 4 SBC, OpenCR microcontroller, LDS-02 360° LiDAR, and LiPo power supply.
  - *Software*: ROS 2 Jazzy running on Ubuntu 24.04 LTS.
  - *Edge Nodes*:
    - `emulated_sensor`: Ingests physical $(x, y)$ coordinates and outputs realistic Gaussian chemical plumes ($\text{NH}_4^+$, DO) defined in `reach_frame.yaml`.
    - `edge_buffer` & `link_gate`: Resilient store-and-forward queue ensuring zero data loss during wireless dropouts.
- **Navigation & Safety Stack**:
  - AMCL localization on a 2D occupancy grid with a custom *Keepout River Boundary Filter*.
  - Nav2 planner, controller, and behavior tree recovery nodes.
  - Collision Monitor actively listening to LiDAR safety zones.
- **Digital Twin & Mirror Stack**:
  - `twin_core`: Analytical 2D NumPy advection-diffusion solver calculating posterior source probabilities across candidate outfalls.
  - `mission_controller`: State machine orchestrating exploration, dwell pauses, and upstream retasking.
  - `sync_monitor`: Continuous divergence tracking between physical `/odom`, AMCL pose, and Gazebo `ghost_follower`.
  - `gateway_node`: WebSocket server (port `:8765`) streaming JSON telemetry to CesiumJS 3D WebGL (port `:8080`).
- **Presenter Spoken Script (Target: 1:30 min)**:
  > *"Here is the complete software and hardware pipeline of our laboratory PoC:*
  > *On the physical robot, ROS 2 Jazzy runs on a Raspberry Pi 4, interfacing with the OpenCR board and LiDAR. An edge buffer guarantees zero telemetry loss during Wi-Fi drops.*
  > *For navigation, Nav2 and AMCL enforce a Keepout River Filter, ensuring the robot remains within safe corridor boundaries.*
  > *In the Digital Twin engine, our lightweight 2D NumPy solver evaluates plume dispersion, while a synchronization monitor cross-references physical odometry against our Gazebo ghost follower in real time.*
  > *Finally, a gateway node streams coordinates and chemical readings via WebSockets to our 3D CesiumJS dashboard."*

### Slide 11: Experimental Setup & Comparative Baseline
*The Controlled Experiment: Baseline Blind Patrol vs. Adaptive Digital Twin*
- **The Physical Arena Setup**:
  - Calibrated rectangular indoor arena corridor representing a scaled 500-meter reach of the Pegnitz River.
  - **3 Candidate Outfall Locations (A, B, C)** positioned along the arena perimeter.
  - In any test run, one candidate outfall is configured as the active simulated contamination emitter.
- **The Controlled Comparative Baseline**:
  - *Control Group (Blind Baseline Patrol)*:
    - Robot executes a fixed-route patrol navigating predefined waypoints without real-time feedback (analogous to traditional scheduled monitoring).
    - Result: Robot crosses the plume boundary, logs an elevated reading in its internal memory, but blindly drives past without investigating. The active outfall remains unidentified!
  - *Experimental Group (PlumeTrace Adaptive Closed Loop)*:
    - Robot detects ammonium spike ($> 0.6\ \text{mg/L}$), triggers Sampling Pause (`DWELL_AND_ANALYZE`), streams telemetry to the Digital Twin.
    - Twin solver identifies the active outfall candidate with $> 90\%$ probability, computes an upstream waypoint, and pushes it to Nav2.
    - Result: Robot autonomously turns upstream, follows the concentration gradient, and stops directly at the leaking outfall pipe!
- **Presenter Spoken Script (Target: 1:15 min)**:
  > *"To rigorously prove our system's value, we established a comparative baseline experiment in our calibrated lab arena featuring three candidate outfall locations: A, B, and C.*
  > *In the Control Baseline – which mimics current scheduled monitoring – the robot executes a fixed patrol line. It crosses the pollution plume, but blindly drives past, leaving the source completely undiscovered.*
  > *In contrast, our Adaptive PlumeTrace system immediately detects the spike, pauses to analyze, consults the Digital Twin, and receives an upstream waypoint. The robot actively navigates to the source and stops directly at the faulty outfall marker, proving the power of closed-loop autonomy."*

---

## 5. Demonstration (Video / Slides)
*Target Audience: Technical Experts (with Stakeholder Relevance)*
*Format: High-Definition Split-Screen Video Demonstration*

### Video Demonstration Storyboard (4 Synchronized Panels)
- **Visual Layout of the Video**:
  - **Panel 1 (Top Left)**: Physical TurtleBot3 navigating inside the physical lab arena.
  - **Panel 2 (Top Right)**: Gazebo Harmonic co-simulation mirror displaying physics, obstacles, and ghost robot follower.
  - **Panel 3 (Bottom Left)**: 2D Plume Inversion Solver displaying real-time Gaussian gradient contours and candidate outfall probabilities.
  - **Panel 4 (Bottom Right)**: CesiumJS 3D Digital Twin displaying the Nuremberg LOD2 city view, real-time robot position, and live stakeholder alerts.
- **Sequential Demo Scenes**:
  1. *Scene 1: Patrol & Baseline Comparison*: Robot begins corridor navigation; baseline trajectory crosses plume and continues blindly, whereas adaptive mode prepares for detection.
  2. *Scene 2: Threshold Breach & Sampling Pause*: Robot reaches plume boundary ($> 0.6\ \text{mg/L}\ \text{NH}_4^+$); immediately halts forward motion (`DWELL_AND_ANALYZE`); telemetry packet transmitted upstream.
  3. *Scene 3: Twin Inversion & Goal Dispatch*: Digital Twin calculates posterior probabilities across Outfalls A, B, and C; generates updated Nav2 waypoint directed toward active Outfall B; pushes goal downstream in $< 35\ \text{s}$.
  4. *Scene 4: Upstream Intercept & Source Localization*: Robot resumes motion, follows the gradient upstream, and stops precisely at Candidate Marker B; CesiumJS dashboard updates Outfall B health score to RED and broadcasts alert.

### DTAS Criteria Verification Checklist
- [x] **1. Bidirectional Communication**: Real-time physical telemetry (`/odom`, `/scan`, `/ammonia`) streamed upstream; dynamic Nav2 goal waypoints pushed downstream from cloud twin.
- [x] **2. State Synchronisation**: Continuous pose and chemical synchronization across physical TurtleBot, AMCL localization, Gazebo `ghost_follower`, and CesiumJS 3D coordinate frames with active drift monitoring.
- [x] **3. Environmental Interaction**: Physical 360° LiDAR interacting with lab arena boundaries + tight cyber-physical coupling where the robot's physical $(x, y)$ position interacts with the simulated spatial chemical field.

---

## 6. Evaluation and Technical Reflection (4 Slides)
*Target Audience: Technical Experts*

### Slide 12: Implementation Scope Matrix
*Detailed Accounting of Planned vs. Delivered Functionality*

| Subsystem | Feature / Capability | Implementation Status | Technical Notes |
| :--- | :--- | :--- | :--- |
| **Robotics Platform** | TurtleBot3 ROS 2 Jazzy bringup & OpenCR control | **Delivered** | Fully validated on embedded hardware |
| **Robotics Platform** | LDS-02 2D LiDAR scanning & safety collision stop | **Delivered** | Dual-zone Collision Monitor operational |
| **Robotics Platform** | Physical aquatic deployment (ASV on Pegnitz River) | **Not Implemented** | Out of scope for dry lab course framework |
| **Sensing & Telemetry** | Emulated spatial chemical sensor node ($\text{NH}_4^+$, DO) | **Delivered** | Gaussian dispersion based on $(x, y)$ position |
| **Sensing & Telemetry** | Resilient store-and-forward edge buffer | **Delivered** | Zero telemetry loss across simulated network drops |
| **Sensing & Telemetry** | Submerged physical ion-selective wet probes | **Not Implemented** | Replaced by cyber-physical emulated node |
| **Digital Twin Engine** | 2D Analytical NumPy Advection-Diffusion Inversion | **Delivered** | Rapid analytical solver ($< 3\ \text{s}$ computation) |
| **Digital Twin Engine** | Dynamic Nav2 goal generation & mission state machine | **Delivered** | Sampling pause and upstream retasking |
| **Digital Twin Engine** | Full 3D Hydrodynamic CFD solver (OpenFOAM) | **Not Implemented** | Intentionally omitted due to $< 2\ \text{min}$ SLA budget |
| **Visualization & AI** | CesiumJS 3D Globe with Bavarian LOD2 OpenData | **Partially Implemented** | WebGL pipeline operational; styling in progress |
| **Visualization & AI** | Model Context Protocol (MCP) server for AI chat | **Delivered** | Standardized MCP schema for external LLM query |

### Slide 13: Testing, Calibration & Target Evaluation
*Methodology, Target SLAs, and Experimental Validation*
- **Core SLA Targets & Evaluation Metrics**:
  - *Round-Trip Time (RTT)*: Telemetry generation $\to$ Twin processing $\to$ Nav2 goal execution. SLA ceiling: $< 120\ \text{s}$; Target lab turnaround: $\approx 33\text{--}35\ \text{s}$.
  - *Regulatory Alert Latency*: Time from threshold breach ($> 0.6\ \text{mg/L}$) to CesiumJS dashboard alert: Target $< 60\ \text{s}$.
  - *Positional Drift Tolerance*: Measured deviation between physical odometry dead-reckoning and AMCL map coordinates over 10-minute test runs.
  - *Source Localization Accuracy*: Frequency with which the adaptive system correctly identifies the true active outfall out of 3 candidates (Target: $> 90\%$).
- **Calibration Procedures**:
  - Odometry wheel-slip calibration on dry arena surface.
  - Laser scan angular alignment with arena boundaries.
  - Synthetic plume parameter tuning to match real Pegnitz seasonal flow velocities ($0.3\text{--}0.8\ \text{m/s}$).

### Slide 14: Strengths, Limitations & Risk Reflections
*Critical Engineering Self-Assessment*
- **Key System Strengths**:
  - *Validated Cyber-Physical Closed Loop*: Operates on real embedded hardware with real sensor noise, wheel slip, and wireless DDS communications.
  - *Lightweight Analytical Solver*: Avoids heavy cloud CFD latency, enabling genuine real-time retasking in $< 35\ \text{seconds}$.
  - *Direct Regulatory Alignment*: Parameter thresholds and alerts directly reflect EU WFD and German OGewV statutory standards.
- **Key System Limitations**:
  - *Terrestrial Proxy Platform*: Using a wheeled ground robot in a dry arena means hydrodynamic drag, surface waves, 3D depth gradients, and river currents are modeled in software rather than experienced physically.
  - *Synthetic Chemistry Node*: Relies on spatial coordinate mapping rather than physical wet-chemistry reaction kinetics.
- **Risk Assessment Reflection**:
  - *Lab Wi-Fi Latency & Dropouts*: Successfully mitigated via CycloneDDS domain isolation and the onboard `edge_buffer`.
  - *Computational Bottleneck*: Mitigated by strictly avoiding heavy CFD in favor of our 2D NumPy advection-diffusion solver.
  - *Odometry Wheel Slip*: Identified as the primary physical error source, requiring continuous AMCL correction.

### Slide 15: Technical Reflections & Future Roadmap
*Engineering Insights and Next Development Steps*
- **Key Engineering Reflections**:
  - *Lightweight Data Contracts*: 30-second telemetry batching provided the optimal trade-off between responsiveness and avoiding wireless network saturation.
  - *Decoupling Safety from High-Level Autonomy*: Implementing the emergency STOP cloud directly in the local Collision Monitor ensured safety even if the high-level Nav2 planner experienced latency.
- **Production Roadmap**:
  1. *Aquatic Hardware Port*: Transfer the ROS 2 navigation and safety stack from the TurtleBot3 onto an Autonomous Surface Vessel (catamaran hull) equipped with physical water thrusters.
  2. *Physical Sensor Wet-Testing*: Integrate physical ion-selective ammonium probes and optical dissolved oxygen sensors.
  3. *Bathymetric Sonar Integration*: Mount downward-looking acoustic sounders to map riverbed bathymetry, culvert siltation, and sediment scour.
  4. *Live State API Ingestion*: Connect the cloud twin directly to real-time telemetry APIs from the Bavarian *Landesamt für Umwelt* (LfU).

---

## Defence Master Q&A Cheat Sheet
*Key Answers for Likely Jury Questions*

1. **Why TurtleBot instead of a boat?**
   - *"The TurtleBot3 Burger was the course-provided hardware platform. It acts as an accessible cyber-physical proxy, proving that our closed-loop telemetry, state synchronization, and dynamic retasking operate on real embedded hardware under real noise and communication constraints."*
2. **Why not static sensors?**
   - *"Static sensors suffer from point dilution. They only indicate that pollution passed by, but cannot determine whether the source is 50 meters or 500 meters upstream. PlumeTrace actively traces the concentration gradient back to the exact leaking outfall."*
3. **Why 2D NumPy instead of full CFD?**
   - *"A full 3D CFD simulation takes hours to compute. Our operational SLA requires recomputing navigation goals in under 120 seconds. Our 2D advection-diffusion analytical solver runs in under 3 seconds, delivering actionable real-time guidance."*
4. **How do citizens benefit?**
   - *"Through our Model Context Protocol (MCP) server, citizens can query AI assistants in natural language: 'Can I surf at Fuchslochwelle today?'. The AI translates complex chemistry into an immediate, intuitive Traffic Light warning (Green, Yellow, Red)."*
