# General Information

Central knowledge base for project scope, background research, technical specifications, and presentation requirements for EuroTeQ Eindhoven T3.

---

## Documents Index

1. [**`project_overview.md`**](project_overview.md)
   - Comprehensive overview of the Pegnitz River CSO monitoring project.
   - UN SDG 6.3 alignment, course hardware proxy context (TurtleBot3 as ASV proxy), stakeholder analysis (*Wasserwirtschaftsamt*, *LfU*), and architecture.
2. [**`pegnitz_strategy.md`**](pegnitz_strategy.md)
   - Strategic rationale for selecting the Pegnitz River (Nuremberg, Bavaria) over generic global waterways.
   - Bavarian LOD2 OpenData integration, realistic transient CSO dynamics, and regulatory compliance (EU WFD, German OGewV, $\text{NH}_3\text{-N} > 0.6\ \text{mg/L}$ acute limit).
3. [**`international_benchmarks.md`**](international_benchmarks.md)
   - International comparative analysis (Germany, India CPCB Classes A–E for Yamuna, Kenya standards, UK).
   - Biochemical justification for Ammonia ($\text{NH}_3\text{-N}$) and Dissolved Oxygen ($\text{DO}$).
   - The Riverbank Accessibility Constraint (single-bank inspection corridor and cross-stream dispersion).
4. [**`technical_specifications.md`**](technical_specifications.md)
   - Technical specifications for ROS 2 nodes, Mock Water Quality Node ($\text{NH}_3\text{-N}$, $\text{DO}$), 2D NumPy dispersion model, CycloneDDS networking, and calibration protocols.
5. [**`course_gate_mapping.md`**](course_gate_mapping.md)
   - EuroTeQ rubric alignment: Gate 1 (Virtual Lab in Gazebo) and Gate 2 (Physical Lab Validation on TurtleBot3 Burger + HP Z-Book).
   - Technical references: TUM 3DCityDB and Cesium Sandcastle 3D Tiles River documentation.
6. [**`team_knowledge_base.md`**](team_knowledge_base.md)
   - The master 24-point Q&A guide covering every core concept, architectural choice, mathematical assumption, and defence talking point.
7. [**`presentation_requirements.md`**](presentation_requirements.md)
   - Official defence guidelines, 6-part presentation rubric, audience targeting, slide limits, and DTAS evaluation criteria.
8. [**`open_questions_and_backlog.md`**](open_questions_and_backlog.md)
   - Identified design tensions, technical calibration items (sampling pause, advection parameters, outfall triplet, DTAS defense points), and engineering backlog to address in later phases.

---

## Project Snapshot
- **Domain**: Water Quality & Environmental Autonomous Robotics
- **River Context**: Pegnitz River (Nuremberg, Bavaria, Germany)
- **Primary Asset**: TurtleBot3 Burger (ROS 2 Humble / Nav2 / slam_toolbox)
- **Digital Twin**: Python Mediator + 2D NumPy Advection-Diffusion Plume Model + 3DCityDB / Cesium (Bavarian LOD2 OpenData)
- **Regulatory Frameworks**: EU Water Framework Directive (WFD), German *Oberflächengewässerverordnung* (OGewV)
- **Regulatory Triggers**: Ammonia Nitrogen ($\text{NH}_3\text{-N} > 0.6\ \text{mg/L}$) and Dissolved Oxygen ($\text{DO}$) depletion
