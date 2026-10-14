#!/usr/bin/env bash
# Lab laptop: check what PlumeTrace needs, build the workspace, print the next step.
# Usage: tools/lab_setup.sh [--pip]     (--pip installs missing Python libraries for this user)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/env.sh"
echo "repo $PLUMETRACE_REPO | workspace $PLUMETRACE_WS | ROS_DISTRO=${ROS_DISTRO:-?} | ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-unset}"
missing_py=()
for m in numpy:numpy yaml:pyyaml scipy:scipy shapely:shapely pymap3d:pymap3d websockets:websockets jsonschema:jsonschema; do
  python3 -c "import ${m%%:*}" 2>/dev/null || missing_py+=("${m##*:}")
done
if [ ${#missing_py[@]} -gt 0 ]; then
  echo "missing Python libraries: ${missing_py[*]}"
  if [ "$1" = "--pip" ]; then
    flag=""; pip install --help 2>/dev/null | grep -q break-system-packages && flag="--break-system-packages"
    pip install --user $flag "${missing_py[@]}" || { echo "pip failed"; exit 2; }
  else
    echo "  run: tools/lab_setup.sh --pip"; exit 2
  fi
fi
missing_ros=()
for p in nav2_map_server nav2_amcl nav2_controller nav2_planner nav2_behaviors nav2_bt_navigator nav2_smoother \
         nav2_lifecycle_manager nav2_regulated_pure_pursuit_controller nav2_navfn_planner nav2_common slam_toolbox; do
  ros2 pkg prefix "$p" >/dev/null 2>&1 || missing_ros+=("$p")
done
if [ ${#missing_ros[@]} -gt 0 ]; then
  echo "MISSING ROS packages: ${missing_ros[*]}"
  echo "  install (needs sudo): sudo apt install $(printf 'ros-%s-%s ' $(for p in "${missing_ros[@]}"; do echo "$ROS_DISTRO" "${p//_/-}"; done))"
  echo "  (slam_toolbox is only needed for mapping; nav2_collision_monitor only for collision_monitor:=true)"
fi
cd "$PLUMETRACE_WS" || exit 3
colcon build --base-paths "$PLUMETRACE_REPO" --symlink-install || { echo "BUILD FAILED"; exit 3; }
echo
echo "Build OK. In every new terminal:  source $PLUMETRACE_REPO/config/env.sh"
echo "Next: tools/lab_check.sh (with the robot bringup running), then docs/LAB_RUNSHEET.md"
