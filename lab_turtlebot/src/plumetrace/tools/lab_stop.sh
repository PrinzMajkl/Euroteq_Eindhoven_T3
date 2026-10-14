#!/usr/bin/env bash
# Stop everything a PlumeTrace launch started on this machine. Matches executables by path only,
# never free text, so it cannot hit the calling shell. It also stops other ROS nodes run from /opt/ros.
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROS="/opt/ros/${ROS_DISTRO:-jazzy}"
pkill -INT -f "^/usr/bin/python3 $ROS/bin/ros2 (bag record|launch plumetrace_sim)" 2>/dev/null
sleep 3
pkill -9 -f "^$ROS/lib/" 2>/dev/null
pkill -9 -f "^/usr/bin/python3 $ROS/lib/" 2>/dev/null
pkill -9 -f "^/usr/bin/python3 .*/install/plumetrace_" 2>/dev/null
pkill -9 -f "^/usr/bin/python3 $ROS/bin/ros2 launch plumetrace_sim" 2>/dev/null
true
