# Project Overview: Pegnitz River CSO Digital Twin

An autonomous, closed-loop robotic system designed to detect, track, and trace transient Combined Sewer Overflows (CSOs) in the Pegnitz River (Bavaria, Germany).

---

## 1. Executive Summary & Vision
Traditional surface water monitoring relies heavily on fixed-interval manual "grab sampling", which frequently misses acute, transient pollution events such as Combined Sewer Overflows (CSOs) during storm events. 

This project addresses **UN SDG 6 (Clean Water and Sanitation)** by establishing an autonomous, closed-loop **Digital Twin** system for dynamic river monitoring. 

### Academic Context & Hardware Proxy Delineation
- **Course Platform Context**: Within the EuroTeQ course infrastructure, physical experimentation is conducted using the **TurtleBot3 Burger** (differential-drive mobile ground robot).
- **Terrestrial Proxy for Autonomous Surface Vessels (ASVs)**: Rather than deploying high-cost marine assets in outdoor waterways during early-stage prototyping, the TurtleBot3 serves as a controlled **terrestrial proxy** in a dry lab arena.
- **Validation Goal**: It validates the cyber-physical pipeline—closed-loop state synchronisation, bidirectional DDS communication, mathematical plume inversion, and dynamic Nav2 replanning under real hardware constraints (odometry slip, network latency, sensor noise)—which directly transfers to surface water ASVs.

### The Closed-Loop Concept
1. Ingests real-time physical telemetry (pose and water quality readings).
2. Triggers an autonomous **Sampling Pause (`DWELL_AND_ANALYZE`)** upon detecting an Ammonia spike ($> 0.6\ \text{mg/L}\ \text{NH}_3\text{-N}$) so the vehicle does not overshoot the plume while awaiting computation.
3. Runs a fast 2D advection-diffusion plume dispersion solver.
4. Dynamically re-tasks the robot via closed-loop feedback (Nav2) to follow chemical gradients directly back to the active discharge source.
5. Renders an interactive 3D digital representation via **3DCityDB** and **Cesium** integrated with Bavarian LOD2 OpenData.

---

## 2. SDG Alignment & Stakeholder Landscape

### UN Sustainable Development Goals (SDGs)
- **SDG 6.3**: Improve water quality by reducing pollution, eliminating dumping, and minimizing release of hazardous chemicals and materials.
- **Indicator 6.3.2**: Proportion of bodies of water with good ambient water quality.

### Primary Stakeholders & Needs
| Stakeholder | Role & Responsibility | Core Need & Pain Point |
| :--- | :--- | :--- |
| **Wasserwirtschaftsamt (WWA)** *(Water Management Office)* | Regional water monitoring & infrastructure oversight | Rapid alerts to acute ecological incidents; pinpointing unmapped or illegal discharge locations. |
| **Bayerisches Landesamt für Umwelt (LfU)** *(State Office for the Environment)* | Environmental regulation, long-term policy & water data collection | Continuous, high-confidence water quality data during transient storm events to calibrate environmental models. |
| **Local Municipalities / Public Utilities** | Wastewater network and sewer overflow operations | Accurate localization of CSO activations to prioritize maintenance and regulatory compliance. |

### Formal Challenge Definition
> *"How can digital twinning be applied to autonomous systems in order to address the challenge of detecting and localizing transient Combined Sewer Overflows (CSOs) for the Wasserwirtschaftsamt and regional environmental authorities?"*

---

## 3. High-Level System Architecture

```text
+---------------------------------------------------------------------------------+
|                                 PHYSICAL DOMAIN                                 |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                        TurtleBot3 Platform                              |   |
|   |  - Sensors: LiDAR (/scan), Odometry (/odom)                             |   |
|   |  - Synthetic Water Quality Node: Ammonia (/water_quality/ammonia) & DO  |   |
|   |  - Actuation: Navigation Stack (Nav2, /cmd_vel)                         |   |
|   +-------------------------------------------------------------------------+   |
+---------------------------------------▲-----------------------------------------+
                                        │ (Bidirectional DDS / CycloneDDS)
                                        │ Telemetry Batches (30s) / Nav2 Waypoints (<2m)
+---------------------------------------▼-----------------------------------------+
|                                  DIGITAL TWIN                                   |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                         Digital Twin Mediator                           |   |
|   |  - Synchronizes physical odometry & chemical sensor streams             |   |
|   |  - Manages bidirectional telemetry & command loops                      |   |
|   +------------------------------------┬------------------------------------+   |
|                                        │                                        |
|   +------------------------------------▼------------------------------------+   |
|   |                     Plume Dispersion Engine                             |   |
|   |  - Lightweight 2D NumPy Advection-Diffusion Model                       |   |
|   |  - Inverts spatial gradient from NH3-N spikes (> 0.6 mg/L)              |   |
|   |  - Predicts upstream outfall coordinates                                |   |
|   +------------------------------------┬------------------------------------+   |
|                                        │                                        |
|   +------------------------------------▼------------------------------------+   |
|   |                     Adaptive Routing Generator                          |   |
|   |  - Computes new intercept Nav2 waypoints                                |   |
|   |  - Dispatches route update back to TurtleBot in < 2 minutes             |   |
|   +-------------------------------------------------------------------------+   |
|                                        │                                        |
|   +------------------------------------▼------------------------------------+   |
|   |                     Visualization & GIS Dashboard                       |   |
|   |  - 3DCityDB + Cesium Web Platform                                       |   |
|   |  - Bavarian LOD2 OpenData 3D riverbank & terrain overlay                |   |
|   +-------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------+
```

---

## 4. Current Progress & Development Status

### Gate 1 Progress (Virtual Lab / Simulation)
- **Gazebo Simulation**: TurtleBot3 Burger model running inside a simulated river corridor environment.
- **Mapping & Localization**: 2D riverbank corridor mapped using `slam_toolbox`.
- **Baseline Patrol**: Fixed-route waypoint navigation established as the control benchmark for evaluation.
- **Topic Pipeline**: Functional ROS 2 topic publishing for `/odom`, `/scan`, and synthetic `/water_quality/ammonia`.

### Transition to Physical Lab Arena
- **Hardware Platform**: TurtleBot3 Burger connected over CycloneDDS.
- **Physical Landmarks (Candidate Outfalls A, B, C)**: Three designated outfall locations marked in the lab arena corridor (e.g., using physical visual landmarks / boxes). Exactly one is active as the simulated effluent discharge source during an evaluation trial.
- **Spatial Sensor Calibration**: Position-dependent mock chemical sensor tuned so that peak $\text{NH}_3\text{-N}$ readings align with the spatial proximity of the active candidate marker.
