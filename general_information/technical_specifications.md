# Technical Specifications & Development Strategy

Detailed technical parameters, component specifications, networking strategy, and testing protocols for the Pegnitz River CSO Digital Twin.

---

## 1. System Components & Parameters

### Mock Water Quality Sensor Node (ROS 2)
- **Synthetic Contaminants**: 
  - Ammonia Nitrogen ($\text{NH}_3\text{-N}$)
  - Dissolved Oxygen ($\text{DO}$)
- **Emission Trigger Threshold**: Peak concentration $> 0.6\ \text{mg/L}\ \text{NH}_3\text{-N}$ indicates an acute CSO event under German OGewV / EU WFD.
- **Emission Function (Advection-Diffusion Formulation)**:
  Incorporates ambient downstream river advection velocity vector $\mathbf{u} = (u_x, 0)$ along the corridor axis:
  $$C(x, y) = C_{\text{background}} + C_{\text{peak}} \cdot \exp\left(-\left(\frac{(x - X_{\text{outfall}} - u_x \Delta t)^2}{2\sigma_x^2} + \frac{(y - Y_{\text{outfall}})^2}{2\sigma_y^2}\right)\right)$$
- **Outfall Candidates**: Three spatial candidates are configured on the corridor map—**Outfall A**, **Outfall B**, and **Outfall C**. In any test run, one candidate is designated as the active emitter.

### Closed-Loop State Machine & Sampling Pause (`DWELL_AND_ANALYZE`)
To prevent the physical TurtleBot3 ($v \approx 0.15\text{--}0.20\ \text{m/s}$) from driving out of the small lab arena ($4\times 6\ \text{m}$) while awaiting cloud twin computation:
1. **`PATROLLING`**: Robot follows fixed baseline patrol waypoints.
2. **`DWELL_AND_ANALYZE` (Sampling Pause)**: When instantaneous $\text{NH}_3\text{-N} > 0.6\ \text{mg/L}$, the robot immediately publishes `cmd_vel = 0` to halt motion, logs high-fidelity sample coordinates, and awaits retasking.
3. **`RETASKED_HOMING`**: The Digital Twin ingests the 30-second telemetry batch, runs the 2D NumPy solver in $< 3\ \text{s}$, and dispatches the upstream waypoint. Nav2 resumes and vectors the robot directly toward the estimated outfall.
- **Effective Turnaround**: Lab PoC completes loop in $\approx 33\ \text{seconds}$, comfortably below the $< 120\ \text{s}$ global river SLA.

### DTAS Environmental Interaction Architecture
The Proof of Concept implements a validated **Hybrid Environmental Interaction**:
1. **Physical Environmental Interaction**: Real 360° LiDAR (`/scan`) continuously senses physical arena boundaries, cardboard outfall markers, and obstacles for real-time costmap updates and collision avoidance in Nav2.
2. **Cyber-Physical Spatial Coupling**: The chemical sensor readings are tightly coupled to the robot's real-world physical position $(x, y)$, ensuring that real wheel slip, motor jitter, and odometry drift directly influence the sampled pollution profile.

### Digital Twin Mediator Node
- **Telemetry Batch Frequency**: 30-second synchronization intervals.
- **Payload**: Timestamp, physical pose $(x, y, \theta)$, covariance, and instantaneous sensor readings ($\text{NH}_3\text{-N}$, $\text{DO}$).
- **State Synchronization Protocol**: Validates spatial drift between physical odometry and digital model; issues dynamic Nav2 waypoints.

### Plume Dispersion Engine
- **Engine Type**: Lightweight 2D NumPy advection-diffusion solver.
- **Design Rationale**: Full Computational Fluid Dynamics (CFD) is computationally prohibitive for real-time edge/cloud operation (< 2 min SLA). A simplified 2D forward-inverse model estimates upstream probability across candidates (A, B, C) in seconds.
- **Adaptive Routing Response Time**: 
  - Real-world River SLA Target: $< 120\ \text{seconds}$.
  - Laboratory PoC Measured Turnaround: $\approx 33\text{--}35\ \text{seconds}$ (30s batch interval + $< 3\text{s}$ solver).
- **Authority Alert Generation**: Dispatched to simulated regulatory dashboard in $< 60\ \text{seconds}$.

### GIS & Visualization Stack
- **3D City Platform**: 3DCityDB.
- **Visualization Client**: CesiumJS WebGL.
- **Geodata Source**: Bavarian LOD2 OpenData (3D riverbank, terrain, and building geometry for Nuremberg/Pegnitz river).

---

## 2. Infrastructure, Networking & Barriers

| Risk / Barrier | Technical Impact | Engineering Mitigation |
| :--- | :--- | :--- |
| **Network Latency & DDS Packet Loss** | Shared laboratory Wi-Fi causes node discovery timeouts and dropped telemetry batches. | Standardize `ROS_DOMAIN_ID` across all host systems and enforce **Eclipse CycloneDDS** middleware with tailored XML buffer tuning. |
| **Computational Overload** | Heavy simulation algorithms delay route calculation beyond the 2-minute closed-loop budget. | Enforce lightweight **2D NumPy** analytical advection-diffusion modeling over full Navier-Stokes CFD solvers. |
| **Physical-to-Digital Positional Drift** | Wheel slip and dead-reckoning drift in physical TurtleBot3 causes divergence from Digital Twin state. | Positional logging, recalibration against visual/arena landmarks, and baseline drift delta quantification. |

---

## 3. Testing, Metrics & Calibration Protocols

### Quantitative Evaluation Metrics
1. **Round-Trip Time (RTT)**:
   - Telemetry Ingest $\to$ Dispersion Solve $\to$ Nav2 Waypoint Dispatch: **Goal $< 120\ \text{seconds}$**.
   - Alert dispatch to stakeholders: **Goal $< 60\ \text{seconds}$**.
2. **Synchronization Accuracy**:
   - Continuous measurement of coordinate divergence between physical robot pose $\mathbf{P}_{\text{physical}}(t)$ and Digital Twin estimated state $\mathbf{P}_{\text{twin}}(t)$.
3. **Source Identification Accuracy**:
   - Probability convergence $P(\text{Outfall}_i \mid \text{samples})$ among potential candidates (A, B, C).
4. **Mission Efficiency (Comparative Baseline)**:
   - **Control**: Fixed-route patrol navigating predefined waypoints without real-time feedback.
   - **Experimental**: Adaptive Digital Twin retasking.
   - **Metrics**: Total distance traveled to locate source, total time elapsed, and number of samples required.
