#!/usr/bin/env bash
# Runs INSIDE the container (docker/run.sh ws). Builds the two workspaces the lablaptop has:
#   ~/turtlebot3_ws   the four ROBOTIS folders of this repo's src/ (underlay; the lablaptop has it already)
#   ~/plumetrace_ws   src/plumetrace, with tools/lab_setup.sh exactly as on the lablaptop
set -e
SRC=/home/ubuntu/lab_turtlebot/src
source /opt/ros/jazzy/setup.bash
cd "$HOME/turtlebot3_ws"
# no --symlink-install here: nothing may point back into (or write to) the ROBOTIS folders
colcon build --base-paths "$SRC/DynamixelSDK" "$SRC/turtlebot3_msgs" "$SRC/turtlebot3" "$SRC/turtlebot3_simulations" \
  --event-handlers console_cohesion- --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
"$SRC/plumetrace/tools/lab_setup.sh" --pip
