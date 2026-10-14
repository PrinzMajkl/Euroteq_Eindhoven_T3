#!/usr/bin/env bash
# Optional: build tf2 0.36.23 into the workspace, over the installed 0.36.22 (no sudo needed).
# 0.36.22 has a lock-order deadlock between tf2_ros waitForTransform and BufferCore that can freeze a
# Nav2 server's TF buffer for good (ros2/geometry2 #982, fixed in 0.36.23 by #989).
# Remove again with: rm -rf $PLUMETRACE_WS/install/tf2 $PLUMETRACE_WS/build/tf2 $PLUMETRACE_WS/overlay
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/env.sh"
have=$(ros2 pkg xml tf2 | grep -o "<version>[^<]*" | cut -d'>' -f2)
echo "tf2 in use: $have"
mkdir -p "$PLUMETRACE_WS/overlay" && cd "$PLUMETRACE_WS/overlay" || exit 1
[ -d geometry2 ] || git clone --depth 1 --branch 0.36.23 https://github.com/ros2/geometry2.git || exit 2
touch COLCON_IGNORE
cd "$PLUMETRACE_WS" && colcon build --base-paths overlay/geometry2/tf2 --packages-select tf2 \
  --cmake-args -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release || exit 3
echo "done: open a new terminal, source config/env.sh; 'ros2 pkg prefix tf2' must print $PLUMETRACE_WS/install/tf2"
