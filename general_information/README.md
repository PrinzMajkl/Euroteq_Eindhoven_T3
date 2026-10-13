# General Information

Central knowledge base for project scope, background research, technical specifications, and presentation requirements for EuroTeQ Eindhoven T3.

---

## Documents Index

1. [**`system_architecture.md`**](system_architecture.md)
   - Complete architectural blueprint and full Mermaid diagram of the PlumeTrace Digital Twin.
   - Node-by-node mapping of physical arena, desktop stack (ROS 2 Jazzy, Gazebo Harmonic), gateway WebSocket (`:8765`), PlumeTrace City View dashboard (CesiumJS), and Bavarian OpenData GIS pipeline.
2. [**`project_overview.md`**](project_overview.md)
   - Comprehensive overview of the Pegnitz River CSO monitoring project.
   - UN SDG 6.3 alignment, course hardware proxy context (TurtleBot3 as ASV proxy), stakeholder analysis (*Wasserwirtschaftsamt*, *LfU*), and architecture.
3. [**`stakeholder_use_cases.md`**](stakeholder_use_cases.md)
   - Deep dive into the 4 core local pillars of the Pegnitz: Public Health & Fuchslochwelle surfers, Urban CSOs & municipal pipes, Knoblauchsland agriculture & groundwater, Drought & fish kill resilience.
   - Citizen "Traffic Light" app vs. Municipal diagnostic dashboard, and 4D adaptive retasking objective function.
4. [**`water_quality_indicators.md`**](water_quality_indicators.md)
   - Breakdown of the 8 parameters monitored by SUN (City of Nuremberg), why they are measured, and their diagnostic value.
   - The fatal frequency bottleneck: Monthly manual grab sampling missing 2-hour transient storm CSOs.
5. [**`mobile_robot_vs_static_sensors.md`**](mobile_robot_vs_static_sensors.md)
   - Strategic and engineering rationale contrasting autonomous mobile robotics with stationary sensor grids.
   - Active gradient tracing, geo-referenced municipal intelligence, 3D corridor/bank erosion mapping, and biofouling economics.
6. [**`quantitative_impacts_and_governance.md`**](quantitative_impacts_and_governance.md)
   - Empirical damage metrics: €1.5M–€5M basin costs, €850k/day EU fines, Wöhrder See fish die-offs.
   - Public health media evidence: The Fuchslochwelle "Durchfall-Welle" (Diarrhea Wave) case.
   - Continuous Spatial Profiler concept (chronic pipe seepage vs emergency spills).
   - Multi-tier governance: State (WWA/LfU) vs. City (Stadt Nürnberg/SUN) UI dashboard perspectives.
7. [**`pegnitz_strategy.md`**](pegnitz_strategy.md)
   - Strategic rationale for selecting the Pegnitz River (Nuremberg, Bavaria) over generic global waterways.
   - Bavarian LOD2 OpenData integration, realistic transient CSO dynamics, and regulatory compliance (EU WFD, German OGewV, $\text{NH}_3\text{-N} > 0.6\ \text{mg/L}$ acute limit).
4. [**`international_benchmarks.md`**](international_benchmarks.md)
   - International comparative analysis (Germany, India CPCB Classes A–E for Yamuna, Kenya standards, UK).
   - Biochemical justification for Ammonia ($\text{NH}_3\text{-N}$) and Dissolved Oxygen ($\text{DO}$).
   - The Riverbank Accessibility Constraint (single-bank inspection corridor and cross-stream dispersion).
5. [**`technical_specifications.md`**](technical_specifications.md)
   - Technical specifications for ROS 2 Jazzy nodes, Mock Water Quality Node ($\text{NH}_3\text{-N}$, $\text{DO}$), 2D NumPy dispersion model, CycloneDDS networking, and calibration protocols.
6. [**`course_gate_mapping.md`**](course_gate_mapping.md)
   - EuroTeQ rubric alignment: Gate 1 (Virtual Lab in Gazebo Harmonic) and Gate 2 (Physical Lab Validation on TurtleBot3 Burger + HP Z-Book).
   - Technical references: TUM 3DCityDB and Cesium Sandcastle 3D Tiles River documentation.
7. [**`team_knowledge_base.md`**](team_knowledge_base.md)
   - The master 24-point Q&A guide covering every core concept, architectural choice, mathematical assumption, and defence talking point.
8. [**`presentation_requirements.md`**](presentation_requirements.md)
   - Official defence guidelines, 6-part presentation rubric, audience targeting, slide limits, and DTAS evaluation criteria.
9. [**`open_questions_and_backlog.md`**](open_questions_and_backlog.md)
   - Identified design tensions, technical calibration items (sampling pause, advection parameters, outfall triplet, DTAS defense points), and engineering backlog to address in later phases.

---

## Project Snapshot
- **Domain**: Water Quality & Environmental Autonomous Robotics
- **River Context**: Pegnitz River (Nuremberg, Bavaria, Germany)
- **Primary Asset**: TurtleBot3 Burger (ROS 2 Jazzy / Nav2 / slam_toolbox / AMCL)
- **Simulation Mirror**: Gazebo Harmonic (`gz sim`, `ros_gz_bridge`, ghost follower)
- **Digital Twin**: Python Mediator + `twin_core` 2D NumPy Advection-Diffusion Plume Model + `sync_monitor`
- **Dashboard UI**: PlumeTrace City View (CesiumJS 3D globe + side panels, WebSocket port `:8765`, HTTP `:8080`)
- **Regulatory Frameworks**: EU Water Framework Directive (WFD), German *Oberflächengewässerverordnung* (OGewV)
- **Regulatory Triggers**: Ammonia Nitrogen ($\text{NH}_3\text{-N} > 0.6\ \text{mg/L}$) and Dissolved Oxygen ($\text{DO}$) depletion
