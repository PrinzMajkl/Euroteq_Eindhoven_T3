#!/usr/bin/env bash
# PlumeTrace environment (ROS 2 Jazzy, real TurtleBot3). Source this in every shell:
#   source <repo>/config/env.sh
# The repo is found from this file's own path; the colcon workspace is <ws> when the repo
# sits anywhere below <ws>/src/, else the repo's parent folder. Override with PLUMETRACE_WS.
_pt_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PLUMETRACE_REPO="$_pt_repo"
if [ -z "${PLUMETRACE_WS:-}" ]; then
  # nearest ancestor folder named src -> its parent is the workspace (e.g. ~/lab_turtlebot/src/plumetrace)
  PLUMETRACE_WS="$(dirname "$_pt_repo")"; _pt_parent="$_pt_repo"
  while [ "$_pt_parent" != / ]; do
    _pt_parent="$(dirname "$_pt_parent")"
    if [ "$(basename "$_pt_parent")" = src ]; then PLUMETRACE_WS="$(dirname "$_pt_parent")"; break; fi
  done
  export PLUMETRACE_WS
fi
# ROS setup scripts reference unset variables; relax nounset while sourcing.
_pt_nounset=0; case $- in *u*) _pt_nounset=1; set +u;; esac
# ROS distro: the one already sourced, else PLUMETRACE_ROS_DISTRO, else jazzy.
if [ -z "${ROS_DISTRO:-}" ]; then
  _pt_distro="${PLUMETRACE_ROS_DISTRO:-jazzy}"
  if [ -f "/opt/ros/$_pt_distro/setup.bash" ]; then source "/opt/ros/$_pt_distro/setup.bash"
  else echo "env.sh: /opt/ros/$_pt_distro/setup.bash not found (set PLUMETRACE_ROS_DISTRO)" >&2; fi
fi
# The lablaptop's pre-built TurtleBot3 workspace, when present (underlay of ours).
if [ -f "$HOME/turtlebot3_ws/install/setup.bash" ]; then source "$HOME/turtlebot3_ws/install/setup.bash"; fi
if [ -f "$PLUMETRACE_WS/install/setup.bash" ]; then source "$PLUMETRACE_WS/install/setup.bash"; fi
[ "$_pt_nounset" = 1 ] && set -u
unset _pt_nounset _pt_repo _pt_parent _pt_distro
# ROS_DOMAIN_ID is NOT set here: it must equal the robot's (tools/lab_check.sh prints both sides).
export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-burger}"
export PLUMETRACE_RUNS="${PLUMETRACE_RUNS:-$HOME/plumetrace_runs}"
export PYTHONPATH="$PLUMETRACE_REPO/plumetrace_twin:$PLUMETRACE_REPO/plumetrace_gateway:$PLUMETRACE_REPO/tools:${PYTHONPATH:-}"
# Optional: Fast DDS UDP only. Off by default; enable with PLUMETRACE_UDP_ONLY=1.
if [ "${PLUMETRACE_UDP_ONLY:-0}" = 1 ]; then
  export FASTRTPS_DEFAULT_PROFILES_FILE="$PLUMETRACE_REPO/config/fastdds_udp.xml"
fi
