# Presentation Directory Index

This directory contains slide decks, visual brand assets, pitch outlines, rehearsal scripts, and vector PDF exports for the EuroTeQ Track 3 project **PlumeTrace** (Autonomous Digital Twin for River Water Protection).

---

## Deliverables & Slides

| File / Asset | Description |
| :--- | :--- |
| **[`presentation_slides.md`](presentation_slides.md)** | **Master Presentation Slides (15 Slides, Bullets Only)**: Clean, slide-by-slide deck content formatted with strict bullet points (no text walls, zero visual imperatives), logical demo flow, and comprehensive Presenter Spoken Scripts. |
| **[`slides_brainstorm.md`](slides_brainstorm.md)** | **Deep Brainstorm & Master Defense Guide**: Comprehensive technical background, macro-economic justifications, regulatory citations (§ 89 WHG), and Master Q&A preparation. |
| **[`finances.txt`](finances.txt)** | **Financial Source Document**: Research notes on municipal retention basin CapEx (€1.5M–€5M+), manual sampling labor costs, and statutory legal liability precedents. |
| **[`brand_style_guide.md`](brand_style_guide.md)** | Graphic identity manual: Calibri typography, 5-color palette, and clean card layout guidelines. |
| **[`assets/logo.jpeg`](assets/logo.jpeg)** | Official PlumeTrace circular brand emblem (Pegnitz river waves, surfer, autonomous surface robot, and sun). |
| **[`assets/ros_architecture_graph.png`](assets/ros_architecture_graph.png)** | rqt_graph-style ROS 2 architecture: robot, Nav2, digital twin nodes, actions, services and the WebSocket path. |
| **[`assets/state_sync_graph.png`](assets/state_sync_graph.png)** | rqt_graph-style multi-layer state synchronization: edge buffer, link, ingest with acknowledgements, sync monitor. |
| **[`generate_ros_diagrams.py`](generate_ros_diagrams.py)** | Regenerates both ROS diagrams (matplotlib). |

---

## Evaluation Rubric Structure (15 Slides / 6 Sections)

- **Section 1: Title Slide (Max 1 Slide)**
  - **Slide 1**: *Project Title, Mission & Team* (Clean title, 6 team members, institutional context)
- **Section 2: Context and Challenge (Max 3 Slides)**
  - **Slide 2**: *The Financial Imperative: What is at Stake?* (€1.5M–€5M basin CapEx, § 89 WHG €6.5M liability, €439–€828 manual sampling vs €8.2k autonomous robot)
  - **Slide 3**: *Environmental Pressures & The Toxic Cocktail* (Ammonia, Diclofenac, PFAS, Hypoxia vs 2–4h storm runoff vs 48h lab delay)
  - **Slide 4**: *Real Human Suffering & The DTAS Challenge* (Fuchslochwelle "Durchfall-Welle", E. coli/norovirus, Otitis, Cercariae Swimmer's Itch + Formal Challenge Definition)
- **Section 3: Technical Solution (Max 3 Slides) – Real-World Vision**
  - **Slide 5**: *The PlumeTrace Ecosystem: Tri-Tier Architecture* (Catamaran ASV with water probe, 360° LiDAR, bathymetric sonar for riverbed *dno*, cloud digital twin, CesiumJS 3D LOD2)
  - **Slide 6**: *Autonomous Closed-Loop Guidance & Digital Twin Rationale* (4D objective function, single-bank reachability inversion, 1 robot vs 50 fouled probes)
  - **Slide 7**: *AI-Native Municipal & Citizen Intelligence* (Model Context Protocol / MCP AI queries, 🟢🟡🔴 Citizen Water Quality Traffic Light, 60s statutory audit reports)
- **Section 4: Proof of Concept (PoC) (Max 3 Slides) – Course Hardware & Lab Validation**
  - **Slide 8**: *PoC Scope & Laboratory Hardware Architecture* (Mandated TurtleBot3 Burger proxy, indoor testing space, ROS 2 Jazzy, chemical sensor emulation)
  - **Slide 9**: *Co-Simulation & Hardware-in-the-Loop Mirror* (Gazebo Harmonic 3D physics mirror, real-time bidirectional telemetry, dynamic plume transport)
  - **Slide 10**: *Multi-Candidate Outfall Discrimination (Testing Scenario)* (Candidate outfalls A/B/C, gradient ascent tracking, baseline vs closed-loop)
- **Section 5: Demonstration (Video / Slides)**
  - **Slide 11**: *End-to-End Live System Demonstration* (Synchronized split-screen video with live team commentary, gradient ascent, and instant alert)
- **Section 6: Evaluation and Technical Reflection (4 Slides)**
  - **Slide 12**: *Empirical Validation Against Course DTAS Criteria* (Sim-to-real < 0.08m, retasking latency < 35s, source localization < 1.2m in < 180s)
  - **Slide 13**: *Operational & Economic Advantage* (Manual €828 vs €10/day, 100x temporal density, CapEx protection)
  - **Slide 14**: *System Limitations & Failure Modes* (River debris, prop weeds, probe biofouling, acoustic cavitation, GPS multipath)
  - **Slide 15**: *Future Roadmap & Project Transferability* (Catamaran on Pegnitz, multi-agent fleet, Isar/Rhine scaling, riverbed renaturation)

