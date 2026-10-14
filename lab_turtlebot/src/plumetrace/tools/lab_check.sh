#!/usr/bin/env bash
# Lab laptop, robot bringup running: record what the robot publishes and what this laptop has.
# Writes lab/reports/<time>.txt (commit it) and prints the launch arguments to use.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$HERE/config/env.sh"
OUT="$HERE/lab/reports/$(date +%Y%m%d-%H%M%S).txt"; mkdir -p "$(dirname "$OUT")"
{
  echo "## os"; lsb_release -ds 2>/dev/null; python3 --version; nproc
  echo "## env"; env | grep -E "^(ROS_|RMW_|TURTLEBOT3|LDS_|FASTRTPS|FASTDDS|CYCLONE)"
  echo "## packages"
  for p in nav2_bringup nav2_amcl nav2_collision_monitor nav2_loopback_sim slam_toolbox cartographer_ros \
           turtlebot3_bringup turtlebot3_node turtlebot3_navigation2 turtlebot3_gazebo foxglove_bridge tf2 rclpy; do
    printf "%s: " "$p"; ros2 pkg xml "$p" 2>/dev/null | grep -o "<version>[^<]*" || echo MISSING
  done
  echo "## python"
  for m in numpy scipy shapely pymap3d websockets yaml; do
    printf "%s: " "$m"; python3 -c "import $m;print(getattr($m,'__version__','ok'))" 2>&1 | tail -1
  done
  ros2 daemon start >/dev/null 2>&1; sleep 6   # give discovery over Wi-Fi time
  echo "## nodes"; ros2 node list
  echo "## topics"; ros2 topic list -t
  echo "## cmd_vel"; ros2 topic info /cmd_vel -v
  echo "## scan"; timeout 10 ros2 topic echo /scan --once | grep -E "frame_id|angle_|range_m|scan_time"
  timeout 8 ros2 topic hz /scan 2>&1 | tail -2
  echo "## odom"; timeout 8 ros2 topic hz /odom 2>&1 | tail -2
  echo "## clock offset (robot odom stamp vs this laptop)"
  timeout 15 python3 - <<'PY'
import time, rclpy
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
rclpy.init(); n = rclpy.create_node('pt_clock_check'); d = []
n.create_subscription(Odometry, '/odom', lambda m: d.append(time.time() - (m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)), qos_profile_sensor_data)
t0 = time.time()
while len(d) < 20 and time.time() - t0 < 10: rclpy.spin_once(n, timeout_sec=0.2)
print('no /odom received' if not d else f'laptop - robot = {sorted(d)[len(d)//2]:+.3f} s over {len(d)} msgs (frame {"ok" if abs(sorted(d)[len(d)//2]) < 0.3 else "TOO LARGE: sync the clocks, Nav2 will reject transforms"})')
PY
  echo "## battery"; timeout 8 ros2 topic echo /battery_state --once | grep -E "voltage|percentage"
} > "$OUT" 2>&1
cat "$OUT"
echo
if grep -A12 "^## cmd_vel" "$OUT" | grep -q "TwistStamped"; then echo "=> /cmd_vel is TwistStamped: use stamped:=true (the default)"
elif grep -A12 "^## cmd_vel" "$OUT" | grep -q "msg/Twist"; then echo "=> /cmd_vel is Twist: add stamped:=false to every launch"
else echo "=> /cmd_vel not seen: is the bringup running, and is ROS_DOMAIN_ID the same on robot and laptop?"; fi
echo "report: $OUT"
