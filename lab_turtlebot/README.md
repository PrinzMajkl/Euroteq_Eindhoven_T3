# lab_turtlebot

PlumeTrace on a TurtleBot3 Burger (ROS 2 Jazzy): a robot samples a virtual pollution plume along a taped
river in the lab arena, a digital twin works out which outfall is leaking, and a Cesium dashboard shows it
on the real river (Pegnitz, Nürnberg) with an incident workflow for the local authorities.

**How it works (for presenting): [ARCHITECTURE.md](ARCHITECTURE.md)**: layers, nodes, topics, services,
actions and UML diagrams.

## State (2026-10-15)

| Part | State |
| --- | --- |
| Simulation (Gazebo, Jazzy container) | Scenarios A, B, C each ended with the right outfall ([SIMULATION.md](src/plumetrace/docs/SIMULATION.md)) |
| Real robot | Bringup and Nav2 run from the lablaptop (`ROS_DOMAIN_ID=32`, robot `turtlebot@192.168.8.32`); first mission ran, but stops failed from a wrong heading, so no confident result yet |
| One-command demo | `tools/start_demo.sh`: relay, Cloudflare link, robot bringup over ssh, missions A/B/C, RViz |
| Mission runner | `tools/run_abc.py`: continuous rounds (start mark → mission → start mark → ...), each with a secret leaking outfall (A, B or C at random), mock sensor settings `--sensor-*` shown on the dashboard, `--strategy adaptive` (ends at 95 %) or `sweep` (6 fixed stops along the whole bank); self-localisation and drive to the start mark first, PASS only at ≥ 95 % confidence |
| Self-localisation | `tools/localize.py` + `localization_monitor` (mirror check, global search, HOLD and resume during a mission); tested against stand-ins, thresholds from simulation |
| Dashboard | Robot, plume (estimated / true), samples, outfall probabilities, battery, runs table, incident workflow (Pegnitz escalation chain, public warning request); minimal layout |
| Open issues | Jerky motion: [jerky_motion_diagnosis.md](src/plumetrace/docs/jerky_motion_diagnosis.md) (parameter fixes proposed, not applied); localisation thresholds not yet tuned on the real lab |
| Tests | 51 unit tests: `cd src/plumetrace && python3 -m pytest -q tests` |

## Quick start (lablaptop)

```bash
cd ~/Euroteq_Eindhoven_T3 && git pull
cd lab_turtlebot/src/plumetrace && tools/lab_setup.sh
tools/start_demo.sh
```

Robot on the start mark first. Stop everything with `tools/start_demo.sh stop`. Every step and command:
[LAB_RUNSHEET.md](src/plumetrace/docs/LAB_RUNSHEET.md).

## Folders

| Path | What |
| --- | --- |
| `src/plumetrace/plumetrace_msgs` | Message definitions (frozen) |
| `src/plumetrace/plumetrace_twin` | Plume model, emulated sensor, estimator and planner, mission controller, obstacles, self-localisation |
| `src/plumetrace/plumetrace_gateway` | WebSocket gateway between ROS and the dashboard |
| `src/plumetrace/plumetrace_sim` | Lab arena world, maps, Nav2 and SLAM parameters, launch files |
| `src/plumetrace/web` | Cesium dashboard (static page) and Pegnitz incident-response data |
| `src/plumetrace/config`, `data` | Environment script, reach frame, scenarios A/B/C, Pegnitz geometry |
| `src/plumetrace/tools` | `start_demo.sh`, `run_abc.py`, `localize.py`, `relay.py`, lab checks, map and tape tools |
| `src/plumetrace/tests` | Unit tests |
| `src/plumetrace/docs` | Run sheet, simulation results, jerky-motion diagnosis, arena drawing |
| `docker` | Jazzy container for the development laptop (simulation); the lablaptop does not need it |

## Documents

| Document | For |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | How the system fits together, diagrams, talking points |
| [LAB_RUNSHEET.md](src/plumetrace/docs/LAB_RUNSHEET.md) | Running a lab session, from git clone to the demo |
| [SIMULATION.md](src/plumetrace/docs/SIMULATION.md) | What ran in simulation, with numbers |
| [jerky_motion_diagnosis.md](src/plumetrace/docs/jerky_motion_diagnosis.md) | Why the robot moves stop-go and what to change |
| [web/README.md](src/plumetrace/web/README.md) | Dashboard features and messages |
| [CLAUDE.md](CLAUDE.md) | Working notes for the coding agent |

The ROBOTIS packages (`turtlebot3`, `turtlebot3_msgs`, `turtlebot3_simulations`, `DynamixelSDK`) are not in
this repo. The lablaptop has them built in `~/turtlebot3_ws`; this workspace builds on top of that.
