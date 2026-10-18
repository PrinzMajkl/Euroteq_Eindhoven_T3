# Open Questions, Technical Tensions & Development Backlog

This document tracks identified design tensions, technical calibration items, and pending implementation tasks to be addressed in subsequent project stages.

---

## 1. Design Tensions & Calibration Items (To Address Later)

### Item 1: Empirical Verification of Sampling Pause (`DWELL_AND_ANALYZE`)
- **Context**: The robot halts forward motion upon detecting an Ammonia spike ($> 0.6\ \text{mg/L}$) to prevent overshooting the physical lab arena while the Digital Twin computes an updated waypoint.
- **To Address / Calibrate**:
  - [ ] Determine whether the robot should come to a complete standstill (`cmd_vel = 0`) or slow down / loiter in a tight circle.
  - [ ] Measure the exact wall-clock latency between `DWELL` initiation, twin reception over DDS, NumPy solver computation, and Nav2 resumption.
  - [ ] Test recovery behavior if the twin fails to respond within a timeout (e.g., fallback to resume fixed-route patrol after 45 seconds).

### Item 2: Plume Physics & Advection Calibration
- **Context**: The plume must realistically reflect downstream river advection rather than a static, symmetric Gaussian blob.
- **To Address / Calibrate**:
  - [ ] Tune dispersion parameters: river flow velocity $u_x$, longitudinal dispersion coefficient $\sigma_x$, and transverse dispersion coefficient $\sigma_y$.
  - [ ] Validate that the mock sensor node and the 2D NumPy inverse model use identical coordinate frames and flow vectors.
  - [ ] Ensure gradient ascent / probabilistic inversion does not get trapped in local numerical artifacts.

### Item 3: Lab Arena Physical Marker Layout (Candidate Outfalls A, B, C)
- **Context**: Validating probabilistic source identification requires 3 discrete potential outfall sources in the environment.
- **To Address / Calibrate**:
  - [ ] Map out $(X, Y)$ coordinate coordinates for Outfall A, Outfall B, and Outfall C in the 2D occupancy grid (`slam_toolbox`).
  - [ ] Decide physical marker representation in the dry lab (e.g., printed QR/AprilTags or physical boxes).
  - [ ] Implement a configuration flag in the mock sensor node to switch which candidate is the active emitter for a given trial run.

### Item 4: DTAS "Environmental Interaction" Defense Arguments
- **Context**: Evaluators may question whether synthetic chemical readings coupled to physical coordinates qualify as true "environmental interaction".
- **To Address / Rehearse**:
  - [ ] Rehearse the defense explanation: Physical LiDAR interacts with real walls/obstacles and landmarks in the arena, while the synthetic chemical field is coupled directly to the robot's physical real-world odometry (subject to real wheel slip and physical positioning error).
  - [ ] Collect comparison data showing how physical wheel slip produces divergent chemical telemetry profiles compared to idealized pure simulation.

---

## 2. Technical Implementation Backlog (`lab_turtlebot/`)

### Stage 1: ROS 2 Package Scaffolding
- [ ] Create ROS 2 package for water quality mock node (`mock_water_quality_node`).
- [ ] Implement `/water_quality/ammonia` and `/water_quality/dissolved_oxygen` publishers.
- [ ] Add spatial distance calculation relative to active outfall coordinates.

### Stage 2: Digital Twin Mediator & Solver
- [ ] Develop `digital_twin_mediator.py`: Ingest `/odom` and `/water_quality/ammonia` at 30-second batch intervals.
- [ ] Develop `plume_solver.py`: 2D NumPy advection-diffusion inverse model computing $P(\text{Outfall}_i \mid \text{samples})$.
- [ ] Implement Nav2 action client to push dynamic goal poses back to the robot.

### Stage 3: CycloneDDS Lab Network Stabilization
- [ ] Prepare standard `cyclonedds.xml` configuration file with tuned socket buffers and multicast settings.
- [ ] Verify `ROS_DOMAIN_ID` separation to prevent interference with other lab teams.

### Stage 4: Visualization Pipeline
- [ ] Export Bavarian LOD2 geodata for Nuremberg Pegnitz riverbank into 3DCityDB / Cesium 3D Tiles.
- [ ] Build a lightweight CesiumJS web dashboard displaying the live robot pose and chemical heat map.

---

## 3. Evaluation & Comparative Benchmarking Plan

| Test Run | Mode | Active Outfall | Expected Outcome | Metrics to Record |
| :--- | :--- | :--- | :--- | :--- |
| **Run 1 (Baseline)** | Fixed-Route Patrol | Outfall B | Robot detects plume but drives past; does not localize source. | Total travel time, total distance, sample count. |
| **Run 2 (Adaptive)** | Closed-Loop Twin | Outfall B | Robot detects plume, halts, receives waypoint, homes in on Outfall B. | Time to localize, samples to localize, RTT latency. |
| **Run 3 (Robustness)** | Closed-Loop Twin | Outfall C | Evaluates ability to eliminate Outfalls A & B in favor of C. | Probability convergence curve $P(\text{Outfall}_i)$. |

---

## 4. Presentation & Defence Preparation Checklist

- [ ] Record side-by-side video demo: Baseline (blind patrol) vs. Adaptive Twin (closed-loop homing).
- [ ] Capture high-resolution screenshot/recording of Cesium 3D riverbank view with Bavarian LOD2 models.
- [ ] Finalize team member names and slide allocations in `presentation/slides_brainstorm.md`.
- [ ] Rehearse 5-minute pitch timing and slide transition narrative.
