#!/usr/bin/env bash
# One simulated mission in a fresh container, from the host:
#   docker/sim_run.sh <scenario A|B|C> [seed] [extra launch arguments...]
# Starts Gazebo + Nav2 + twin + gateway (sim_mission.launch.py, windows on the desktop when a display is
# reachable), the relay on http://localhost:8090/, starts the mission once Nav2 is active and follows
# /mission/events until the done event. Exit code 0 = done event names the scenario's outfall.
# Logs: docker/runs/<time>-sim-<scenario>/ (launch.log, events.log, CSV logs, rosbag).
# The container keeps running afterwards (dashboard stays live); docker/run.sh down stops it.
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SC="${1:?scenario A, B or C}"; SEED="${2:-1}"; shift; shift || true
TAG="$(date +%Y%m%d-%H%M%S)-sim-$SC"
RUNS=/home/ubuntu/plumetrace_runs
ENVSH="source /home/ubuntu/lab_turtlebot/src/plumetrace/config/env.sh && cd /home/ubuntu/lab_turtlebot/src/plumetrace"
"$HERE/run.sh" up >/dev/null
mkdir -p "$HERE/runs/$TAG"
[ -f "$HERE/runs/relay_key" ] || python3 -c "import secrets; print(secrets.token_hex(8), end='')" > "$HERE/runs/relay_key"
docker exec -d plumetrace-jazzy bash -lc "$ENVSH && exec ros2 launch plumetrace_sim sim_mission.launch.py \
  scenario:=$SC seed:=$SEED autostart:=false gateway_host:=0.0.0.0 run_dir:=$RUNS/$TAG $* > $RUNS/$TAG/launch.log 2>&1"
docker exec -d plumetrace-jazzy bash -lc "$ENVSH && PLUMETRACE_RELAY_KEY=\$(cat $RUNS/relay_key) exec python3 tools/relay.py --bind 0.0.0.0 > $RUNS/$TAG/relay.log 2>&1"
echo "run $TAG: waiting for Nav2 (dashboard: http://localhost:8090/)"
docker exec plumetrace-jazzy bash -lc "$ENVSH && sleep 20 && python3 tools/wait_ready.py 120"
docker exec plumetrace-jazzy bash -lc "$ENVSH; (sleep 2; ros2 topic pub --once /mission/start std_msgs/msg/Empty '{}' >/dev/null &); \
  python3 tools/wait_done.py $SC ${PLUMETRACE_SIM_TIMEOUT:-900} | tee $RUNS/$TAG/events.log | grep --line-buffered -E 'RESULT|\"done\"|goal_result|\"sample\"'"
