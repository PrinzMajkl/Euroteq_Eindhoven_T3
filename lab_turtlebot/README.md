# lab_turtlebot

PlumeTrace on a TurtleBot3 Burger (ROS 2 Jazzy): a robot samples a virtual pollution plume along a taped
river in the lab arena, a digital twin works out which outfall is leaking, and a Cesium dashboard shows it
on the real river (Pegnitz, Nürnberg).

| Path | What |
| --- | --- |
| `src/plumetrace/plumetrace_msgs` | Message definitions |
| `src/plumetrace/plumetrace_twin` | Plume model, emulated sensor, estimator, planner, mission controller, obstacles |
| `src/plumetrace/plumetrace_gateway` | WebSocket gateway between ROS and the dashboard |
| `src/plumetrace/plumetrace_sim` | Lab arena world, maps, Nav2 and SLAM parameters, launch files |
| `src/plumetrace/web` | Cesium dashboard (static page) |
| `src/plumetrace/config`, `data` | Environment script, reach frame, scenarios, reach data |
| `src/plumetrace/tools`, `tests` | Lablaptop scripts, reach tools, unit tests |
| `docker` | Jazzy container for the development laptop (simulation); the lablaptop does not need it |

Run it: [src/plumetrace/docs/LAB_RUNSHEET.md](src/plumetrace/docs/LAB_RUNSHEET.md). Simulation results: [src/plumetrace/docs/SIMULATION.md](src/plumetrace/docs/SIMULATION.md).
Working on it: [CLAUDE.md](CLAUDE.md).

The ROBOTIS packages (`turtlebot3`, `turtlebot3_msgs`, `turtlebot3_simulations`, `DynamixelSDK`) are not in
this repo. The lablaptop has them built in `~/turtlebot3_ws`; this workspace builds on top of that.
