#!/usr/bin/env bash
# Save the map slam_toolbox is publishing to lab/maps/lab_arena.{pgm,yaml} (used by lab_nav / lab_mission).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/env.sh"
mkdir -p "$HERE/lab/maps"
ros2 run nav2_map_server map_saver_cli -f "$HERE/lab/maps/lab_arena" --ros-args -p map_subscribe_transient_local:=true \
  && echo "saved $HERE/lab/maps/lab_arena.yaml (commit lab/maps/ to keep it)"
