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

## How to run

All commands run from `lab_turtlebot/src/plumetrace` unless noted. Full detail and troubleshooting:
[`LAB_RUNSHEET.md`](lab_turtlebot/src/plumetrace/docs/LAB_RUNSHEET.md).

### 1. First time on the lablaptop (5 min)

Ubuntu 24.04 with ROS 2 Jazzy and the TurtleBot3 packages built in `~/turtlebot3_ws`; `ROS_DOMAIN_ID=32` in `~/.bashrc`.

```bash
cd ~ && git clone https://github.com/PrinzMajkl/Euroteq_Eindhoven_T3.git
cd ~/Euroteq_Eindhoven_T3/lab_turtlebot/src/plumetrace
tools/lab_setup.sh --pip      # Python libraries (no sudo) + build the workspace
source config/env.sh
echo $ROS_DOMAIN_ID           # must print 32
```

### 2. Every session: update

```bash
cd ~/Euroteq_Eindhoven_T3 && git checkout main && git pull
cd lab_turtlebot/src/plumetrace && tools/lab_setup.sh
```

### 3. Once per arena setup

| Step | Command | Run sheet |
| --- | --- | --- |
| Tape the river (prints distances from the walls) | `python3 tools/lab_tape_guide.py 0.25` | §2 |
| Map the arena (robot on the start mark) | `ros2 launch plumetrace_sim lab_map.launch.py`, drive a lap with `ros2 run turtlebot3_teleop teleop_keyboard`, then `tools/lab_save_map.sh` | §3 |

### 4. Run the full demo (one command)

1. Put the robot **on the start mark, facing away from the back wall**.
2. Start everything:

   ```bash
   tools/start_demo.sh
   ```

   It opens 5 terminals: **relay** (dashboard on port 8090, prints the operator link with its key), **Cloudflare**
   (public view-only link), **robot** (ssh bringup on the TurtleBot), **missions** (self-localisation, then sweep
   missions in a loop, each with a secret leaking outfall) and **RViz**.
3. Open the dashboard:

   | Link | Shows |
   | --- | --- |
   | `http://localhost:8090/?key=<KEY>` | Authority view, live, commands allowed (key printed in the relay terminal) |
   | `http://localhost:8090/` | Authority view, live, view-only |
   | `http://localhost:8090/index.html?key=<KEY>` | Cesium 3D operator view |
   | `http://localhost:8090/?replay` | Recorded missions instead of live data |

4. If localisation fails and the run asks: put the robot on the start mark and press **Enter**.
5. Stop everything:

   ```bash
   tools/start_demo.sh stop
   ```

### 5. Run one mission by hand (instead of step 4)

Robot bringup running (`ssh turtlebot@192.168.8.32`, then
`export ROS_DOMAIN_ID=32 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-02 && ros2 launch turtlebot3_bringup robot.launch.py`):

```bash
tools/lab_check.sh                                                    # link, clock offset, cmd_vel type
ros2 launch plumetrace_sim lab_mission.launch.py scenario:=B seed:=1  # terminal A
PLUMETRACE_RELAY_KEY=<secret> python3 tools/relay.py                  # terminal B
python3 tools/wait_ready.py 90 && ros2 topic pub --once /mission/start std_msgs/msg/Empty "{}"   # terminal C
python3 tools/wait_done.py B 900                                      # terminal D: RESULT PASS / FAIL
```

### 6. Without the robot

| What | Command |
| --- | --- |
| Unit tests (no ROS needed) | `python3 -m pytest -q tests` |
| Dashboard with recorded missions | `cd web && python3 -m http.server 8080`, open `http://localhost:8080/authority.html` |
| Simulation in Gazebo (Linux with Docker, from `lab_turtlebot/`) | `docker/run.sh image`, `docker/run.sh ws`, then `docker/sim_run.sh B` ([SIMULATION.md](lab_turtlebot/src/plumetrace/docs/SIMULATION.md)) |
| AI access (mock MCP server) | `python3 tools/ai/fuchslochwelle_mcp.py --test` ([README](lab_turtlebot/src/plumetrace/tools/ai/README.md)) |

### When something goes wrong

| Symptom | First check |
| --- | --- |
| Old dashboard at `/` | `git branch --show-current` must be `main`; restart `start_demo.sh`; hard refresh (Ctrl+Shift+R) |
| Robot not in RViz | `ros2 run tf2_ros tf2_echo odom base_footprint`: if it fails, restart the robot bringup |
| Localisation fails | Robot on the start mark, press Enter; `tools/lab_check.sh` for the clock offset |
| Robot moves stop-go | Only one node may publish `/cmd_vel`: `ros2 topic info /cmd_vel -v` |

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
