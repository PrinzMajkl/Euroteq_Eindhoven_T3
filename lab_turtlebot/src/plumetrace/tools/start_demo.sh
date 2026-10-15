#!/usr/bin/env bash
# PlumeTrace demo on the lablaptop: opens 5 terminals for a full real-robot run with the live dashboard.
#
#   tools/start_demo.sh            # open the 5 terminals (gnome-terminal; tmux when there is no display)
#   tools/start_demo.sh --tmux     # force tmux (attach with: tmux attach -t plumetrace)
#   tools/start_demo.sh stop       # stop everything this script started (and all ROS nodes, see lab_stop.sh)
#
#   1 relay       dashboard + live data on http://localhost:8090 (operator link with key printed there)
#   2 cloudflare  public HTTPS link to the relay (view-only for everyone without the key)
#   3 robot       ssh to the TurtleBot3, ROS_DOMAIN_ID=32, turtlebot3_bringup robot.launch.py
#   4 missions    waits for the robot, then tools/run_abc.py --strategy sweep: one mission, leaking outfall picked
#                 at random, 6 fixed stops along the whole bank (past A, B and C)
#   5 rviz        RViz with the PlumeTrace view (map, robot, costmaps, plan)
#
# No Gazebo: with the real robot on domain 32 a simulated robot would publish the same topics.
# For the simulation use sim_mission.launch.py (docs/SIMULATION.md) instead.
#
# Settings (environment variables, defaults in brackets):
#   PLUMETRACE_ROBOT     ssh target of the robot [turtlebot@192.168.8.32]
#   ROS_DOMAIN_ID        [32]
#   PLUMETRACE_RELAY_KEY key for dashboard commands [random per start]
#   RUN_ABC_ARGS         extra arguments for tools/run_abc.py [--confirm --strategy sweep]
#                        e.g. RUN_ABC_ARGS="--confirm --strategy sweep -- xy_goal_tolerance:=0.05"
#                        adaptive instead of the sweep: RUN_ABC_ARGS="--confirm --strategy adaptive"
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT="${PLUMETRACE_ROBOT:-turtlebot@192.168.8.32}"
DOMAIN="${ROS_DOMAIN_ID:-32}"
STATE="${XDG_RUNTIME_DIR:-/tmp}/plumetrace_demo"
SESSION=plumetrace
RUN_ABC_ARGS="${RUN_ABC_ARGS:---confirm --strategy sweep}"

if [ "${1:-}" = stop ]; then
  for f in "$STATE"/*.pid; do
    [ -f "$f" ] || continue
    pid="$(cat "$f")"; kill "$pid" 2>/dev/null && echo "stopped $(basename "$f" .pid) ($pid)"
    rm -f "$f"
  done
  "$REPO/tools/lab_stop.sh"
  command -v tmux >/dev/null && tmux kill-session -t "$SESSION" 2>/dev/null
  echo "Stopped. The bringup on the robot stops when its ssh terminal closes (or Ctrl-C there)."
  exit 0
fi

# --- pre-flight -------------------------------------------------------------------------------------
fail=0
[ -f "$REPO/config/env.sh" ] || { echo "missing $REPO/config/env.sh"; fail=1; }
( source "$REPO/config/env.sh" >/dev/null 2>&1; ros2 pkg prefix plumetrace_sim >/dev/null 2>&1 ) \
  || { echo "plumetrace_sim is not built (workspace $(dirname "$(dirname "$REPO")")):"
       echo "  cd $REPO && tools/lab_setup.sh"; fail=1; }
python3 -c 'import websockets, sys; sys.exit(int(websockets.__version__.split(".")[0]) < 13)' 2>/dev/null \
  || { echo "relay needs websockets >= 13: tools/lab_setup.sh --pip"; fail=1; }
CLOUDFLARED="$(command -v cloudflared || ls "$HOME/.local/bin/cloudflared" 2>/dev/null || true)"
if [ -z "$CLOUDFLARED" ]; then
  echo "cloudflared not found (terminal 2 will only print how to install it). Without sudo:"
  echo "  mkdir -p ~/.local/bin && curl -L -o ~/.local/bin/cloudflared \\"
  echo "    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x ~/.local/bin/cloudflared"
fi
ping -c 1 -W 2 "${ROBOT#*@}" >/dev/null 2>&1 || echo "warning: robot ${ROBOT#*@} does not answer ping (same Wi-Fi?)"
[ "$fail" = 0 ] || exit 1

KEY="${PLUMETRACE_RELAY_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(9))')}"
mkdir -p "$STATE"
rm -f "$STATE"/*.pid

# --- one small script per terminal (avoids nested quoting) -------------------------------------------
prelude() {  # common prelude: repo, ROS environment, domain, keep the terminal open at the end
  cat <<EOF
#!/usr/bin/env bash
cd "$REPO" && source config/env.sh
export ROS_DOMAIN_ID=$DOMAIN
printf '\\033]0;%s\\007' "$1"
echo "== PlumeTrace: $1 =="
fg_job() { child=\$!; echo \$child > "\$1"; trap 'kill \$child 2>/dev/null' INT TERM; wait \$child; wait \$child 2>/dev/null; rm -f "\$1"; }
EOF
}
tail_keep() { echo 'echo; echo "[finished: this terminal stays open]"; exec bash'; }

{ prelude relay
  cat <<EOF
echo "Operator (commands allowed): http://localhost:8090/?key=$KEY"
echo "Viewers (view-only):         http://localhost:8090/  or the cloudflare link in terminal 2"
PLUMETRACE_RELAY_KEY='$KEY' python3 tools/relay.py --port 8090 &
fg_job "$STATE/relay.pid"
EOF
  tail_keep; } > "$STATE/1_relay.sh"

{ prelude cloudflare
  if [ -n "$CLOUDFLARED" ]; then
    cat <<EOF
echo "Public link appears below (https://<random>.trycloudflare.com). It is view-only;"
echo "operators add ?key=$KEY. Anyone with the link sees the page and the Cesium ion token in it."
until curl -s -o /dev/null http://localhost:8090/; do echo "waiting for the relay on :8090 ..."; sleep 2; done
"$CLOUDFLARED" tunnel --no-autoupdate --url http://localhost:8090 &
fg_job "$STATE/cloudflare.pid"
EOF
  else
    echo 'echo "cloudflared is not installed. Install it (no sudo):"'
    echo 'echo "  mkdir -p ~/.local/bin && curl -L -o ~/.local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x ~/.local/bin/cloudflared"'
    echo 'echo "then run: ~/.local/bin/cloudflared tunnel --url http://localhost:8090"'
  fi
  tail_keep; } > "$STATE/2_cloudflare.sh"

{ prelude robot
  cat <<EOF
if timeout 8 ros2 topic list 2>/dev/null | grep -qx /odom; then
  echo "The robot bringup is already running (/odom is visible on domain $DOMAIN): not starting a second one."
  echo "The robot finds itself on the map before mission A (tools/localize.py). To restart the bringup:"
  echo "  ssh -t $ROBOT \"bash -ic 'export ROS_DOMAIN_ID=$DOMAIN TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-02; ros2 launch turtlebot3_bringup robot.launch.py'\""
else
echo "The robot may stand anywhere in the arena: before mission A it finds itself on the map and drives to the start mark."
echo "ssh $ROBOT  (enter the robot password if asked)"
ssh -t -o ServerAliveInterval=5 "$ROBOT" \\
  "bash -ic 'export ROS_DOMAIN_ID=$DOMAIN TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-02; ros2 launch turtlebot3_bringup robot.launch.py'"
fi
EOF
  tail_keep; } > "$STATE/3_robot.sh"

{ prelude missions
  cat <<EOF
echo "Waiting for the robot (/odom and /scan on domain $DOMAIN) ..."
until ros2 topic list 2>/dev/null | grep -qx /odom && ros2 topic list 2>/dev/null | grep -qx /scan; do sleep 2; done
echo "Robot is up. Clock offset and cmd_vel type: tools/lab_check.sh (run it once per session)."
python3 tools/run_abc.py $RUN_ABC_ARGS
EOF
  tail_keep; } > "$STATE/4_missions.sh"

{ prelude rviz
  cat <<EOF
until ros2 topic list 2>/dev/null | grep -qx /odom; do echo "waiting for the robot ..."; sleep 2; done
rviz2 -d "$REPO/plumetrace_sim/rviz/plumetrace.rviz"
EOF
  tail_keep; } > "$STATE/5_rviz.sh"
chmod +x "$STATE"/*.sh

# --- open the terminals ----------------------------------------------------------------------------
NAMES=(1_relay 2_cloudflare 3_robot 4_missions 5_rviz)
if [ "${1:-}" != --tmux ] && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v gnome-terminal >/dev/null; then
  for n in "${NAMES[@]}"; do
    gnome-terminal --window --title="PlumeTrace ${n#*_}" -- bash "$STATE/$n.sh"
    sleep 0.5
  done
  echo "Opened 5 terminals."
elif command -v tmux >/dev/null; then
  tmux kill-session -t "$SESSION" 2>/dev/null
  tmux new-session -d -s "$SESSION" -n "${NAMES[0]#*_}" "bash $STATE/${NAMES[0]}.sh"
  for n in "${NAMES[@]:1}"; do tmux new-window -t "$SESSION" -n "${n#*_}" "bash $STATE/$n.sh"; done
  echo "Started tmux session '$SESSION' (5 windows). Attach: tmux attach -t $SESSION  (switch: Ctrl-b 1..5)"
  echo "RViz needs a display; without one its window fails and the rest keeps running."
else
  echo "Neither gnome-terminal (with a display) nor tmux found. Run these by hand, one per terminal:"
  for n in "${NAMES[@]}"; do echo "  bash $STATE/$n.sh"; done
  exit 1
fi
echo "Dashboard (operator): http://localhost:8090/?key=$KEY"
echo "Stop everything: tools/start_demo.sh stop"
