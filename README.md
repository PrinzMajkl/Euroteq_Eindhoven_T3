# PlumeTrace · EuroTeQ Eindhoven Track 3

An autonomous ground robot patrols the riverbank, samples the water, and a digital twin of the river works out
which outfall is leaking. Authorities see it live in the browser, with an incident workflow and report.

Use case: storm sewer overflows on the **Pegnitz in Nuremberg**. Proof of concept: a **TurtleBot3 Burger** on
**ROS 2 Jazzy** in the lab arena, with the river taped on the floor and the pollution plume simulated by the twin.

## How it works

| Layer | What it does | Where |
| --- | --- | --- |
| Robot | TurtleBot3: 360° LiDAR, wheel odometry, drive commands | stock `turtlebot3_bringup` |
| Navigation | Nav2: AMCL localisation, river keepout zones, planning, recovery, rerouting | [`plumetrace_sim`](lab_turtlebot/src/plumetrace/plumetrace_sim) |
| Digital twin | Plume and sensor model, Bayesian source estimate, adaptive or sweep sampling, mission control, lossless data link | [`plumetrace_twin`](lab_turtlebot/src/plumetrace/plumetrace_twin) |
| Web | WebSocket gateway, relay (one link, view-only without key), authority view, Cesium 3D view | [`plumetrace_gateway`](lab_turtlebot/src/plumetrace/plumetrace_gateway), [`web`](lab_turtlebot/src/plumetrace/web) |
| AI access | Mock MCP server for citizen questions (Fuchslochwelle surf advisor) | [`tools/ai`](lab_turtlebot/src/plumetrace/tools/ai) |

Full explanation with diagrams: [`lab_turtlebot/ARCHITECTURE.md`](lab_turtlebot/ARCHITECTURE.md).

## Repository structure

```text
Euroteq_Eindhoven_T3/
├── lab_turtlebot/           # The implementation (ROS 2 Jazzy workspace, tools, tests, Docker, lab docs)
│   ├── README.md            #   start here for the code
│   ├── ARCHITECTURE.md      #   layers, nodes, topics, actions, diagrams
│   ├── docker/              #   Jazzy container for simulation on a development laptop
│   └── src/plumetrace/      #   packages, web dashboards, tools, tests, docs
├── presentation/            # Slides, speaker scripts, brand guide, diagrams and generators
├── general_information/     # Project brief, research, stakeholders, regulations, requirements
├── AGENTS.md / GEMINI.md    # Rules for contributors and AI agents
└── README.md
```

## Quick start (lablaptop)

```bash
cd ~/Euroteq_Eindhoven_T3 && git pull
```

```bash
cd lab_turtlebot/src/plumetrace && tools/lab_setup.sh
```

```bash
tools/start_demo.sh
```

Put the robot on the start mark first. The dashboard opens at `http://localhost:8090/` (authority view, live);
the Cesium operator view is `/index.html`. Stop with `tools/start_demo.sh stop`. Every step:
[`LAB_RUNSHEET.md`](lab_turtlebot/src/plumetrace/docs/LAB_RUNSHEET.md).

Unit tests (no ROS needed):

```bash
cd lab_turtlebot/src/plumetrace && python3 -m pytest -q tests
```

## Key documents

| Document | For |
| --- | --- |
| [`lab_turtlebot/README.md`](lab_turtlebot/README.md) | Code state, folders, quick start |
| [`lab_turtlebot/ARCHITECTURE.md`](lab_turtlebot/ARCHITECTURE.md) | How the system fits together (for presenting) |
| [`LAB_RUNSHEET.md`](lab_turtlebot/src/plumetrace/docs/LAB_RUNSHEET.md) | Running a lab session |
| [`web/README.md`](lab_turtlebot/src/plumetrace/web/README.md) | Dashboards, relay, gateway messages |
| [`presentation/README.md`](presentation/README.md) | Slides and presentation assets |
| [`general_information/README.md`](general_information/README.md) | Research and project background |

All repository content is in English. Contributor and agent rules: [`AGENTS.md`](AGENTS.md).
