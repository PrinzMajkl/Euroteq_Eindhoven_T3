# Course Gate Mapping & Lab Hardware Architecture

Alignment between conceptual project architecture, EuroTeQ course milestones (Gate 1 & Gate 2), and laboratory execution hardware.

---

## 1. Mapping Conceptual Architecture to EuroTeQ Course Requirements

| Architecture Component | Implementation in the EuroTeQ Lab | Course Rubric Step |
| :--- | :--- | :--- |
| **Physical Robot Platform** | **TurtleBot3 Burger** (Gazebo simulation + physical hardware). Navigates a 2D floor map representing the riverbank corridor. | Setup, Simulation Setup, Physical Bring-up |
| **Edge Autonomy Layer** | Distributed between **TurtleBot3 SBC (Raspberry Pi)** and **HP Z-Book ground laptop**. Standard Nav2 and SLAM nodes (`slam_toolbox`) handle navigation, waypoints, and obstacle avoidance. | Obstacle Detection & Avoidance |
| **Water Quality Sensor Payload** | **Mock Sensor Node**: ROS 2 Python node emitting synthetic $\text{NH}_3\text{-N}$ and $\text{DO}$ values based on real-time robot $(x, y)$ coordinates in the map. | Environmental Interaction |
| **Digital Layer (Cloud Twin)** | **Digital Entity 2**: Python backend running on the laptop/server executing the 2D advection-diffusion NumPy dispersion model and threshold evaluations ($> 0.6\ \text{mg/L}$). | DT Integration Node / Mediator, Plume Dispersion Engine |
| **Dynamic Closed-Loop Retasking** | **Closed Feedback Loop**: Digital Twin detects exceedance, triggers Sampling Pause, computes upstream source probabilities, and pushes a dynamic Nav2 goal. | Physical–Digital Integration, Synchronization & Tolerances |
| **3D Geospatial Twin & UI** | **3DCityDB + CesiumJS**: Pre-rendered 3D environment with Bavarian LOD2 OpenData displaying riverbank, terrain, outfall markers, and live telemetry. | Visualization Dashboard & Context Modeling |

---

## 2. Technical Gate Breakdown

```text
+-------------------------------------------------------------------------------------------------+
|                                     TECHNICAL GATES OVERVIEW                                    |
+------------------------------------------------+------------------------------------------------+
| GATE 1: VIRTUAL LAB (SIMULATION)               | GATE 2: PHYSICAL LAB VALIDATION                |
| - 100% Feasible outside lab                    | - High Feasibility in EuroTeQ Dry Lab Arena     |
| - TurtleBot3 Burger in Gazebo                  | - Real TurtleBot3 Burger (Raspberry Pi + LiDAR)|
| - 2D corridor map via slam_toolbox             | - CycloneDDS with matching ROS_DOMAIN_ID       |
| - Synthetic /water_quality/ammonia topic       | - Physical Outfall Markers (Candidates A, B, C)|
| - Python 2D NumPy advection-diffusion solver   | - Sampling Pause (DWELL) & dynamic Nav2 goal   |
| - Baseline fixed-route patrol mapped           | - Odometry vs. Digital Twin drift delta logging|
+------------------------------------------------+------------------------------------------------+
```

### Gate 1: Virtual Lab / Simulation (100% Feasible Outside Lab)
- **Simulation Environment**: Spin up TurtleBot3 Burger inside Gazebo. Build a 2D obstacle corridor using `slam_toolbox`.
- **Entity 1 (Simulation Asset)**: Gazebo/RViz robot publishing `/odom`, `/scan`, and synthetic `/water_quality/ammonia` (1 Hz).
- **Entity 2 (Plume Engine)**: Python backend running the 2D NumPy advection-diffusion model.
- **DT Mediator Node**: ROS 2 bridging node synchronizing robot state with the dispersion grid and returning re-tasked Nav2 goals upon threshold exceedance.
- **Verification Metrics**: Quantify Round-Trip Time (RTT) between synthetic telemetry generation and plume recalculation.

### Gate 2: Physical Lab Validation (High Feasibility in Lab Arena)
- **Physical Bring-Up**: Re-route the Mediator node from simulated Gazebo topics to the physical TurtleBot3 topics (`/odom`, `/cmd_vel`, `/scan`).
- **Physical Environmental Interaction**:
  - Place 3 physical markers (cardboard boxes) in the dry lab corridor representing **Candidate Outfalls A, B, and C**.
  - As the physical robot approaches the active candidate coordinate, the mock sensor node publishes the peak $\text{NH}_3\text{-N}$ spike.
  - The robot initiates the **Sampling Pause (`DWELL_AND_ANALYZE`)**.
  - The Digital Twin evaluates candidate probabilities and autonomously retasks the robot via Nav2 to home in on the active marker.
- **Hardware Synchronization & Drift Logging**: Track divergence between raw wheel odometry and the Digital Twin's coordinate frame over 10-minute patrol runs, logging network jitter and positional drift.

---

## 3. Distributed Edge & Ground Station Architecture

```text
[TurtleBot3 Burger SBC]                [HP Z-Book Ground Station]
- Raspberry Pi 4                       - Ubuntu 22.04 LTS / ROS 2 Humble
- OpenCR Motor Controller              - Eclipse CycloneDDS (ROS_DOMAIN_ID=42)
- 360° LiDAR LDS-02                    - Nav2 Navigation Stack
- Local /odom, /scan publishers        - Digital Twin Mediator Node
- Telemetry buffer                     - 2D NumPy Dispersion Solver
                                       - 3DCityDB + Cesium Web Server
```

---

## 4. Key Reference Links & Tool Documentation

- [**TUM 3DCityDB Project**](https://www.asg.ed.tum.de/gis/projekte/3dcitydb/): Open-source CityGML/CityJSON database schema for storing and exporting semantic 3D city models.
- [**Cesium Sandcastle: 3D Tiles Property LOD River**](https://sandcastle.cesium.com/?id=3d-tiles-property-lod-river): Reference implementation for displaying 3D river geometry and environmental properties in Cesium.
- [**GeodatenBayern OpenData Portal**](https://geodaten.bayern.de/): Official source of Bavarian LOD2 building models and digital elevation data for the Pegnitz river in Nuremberg.
