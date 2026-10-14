# Jazzy build and simulation image for lab_turtlebot (development laptop only).
# It mirrors what the lablaptop has from apt and pip; the ROBOTIS packages and plumetrace are
# NOT in the image: docker/build_ws.sh builds them from the mounted repo into Docker volumes.
FROM osrf/ros:jazzy-desktop

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
      ros-jazzy-slam-toolbox ros-jazzy-cartographer-ros \
      ros-jazzy-ros-gz \
      ros-jazzy-hls-lfcd-lds-driver ros-jazzy-tf-transformations ros-jazzy-xacro \
      ros-jazzy-robot-state-publisher ros-jazzy-rviz2 \
      python3-pip python3-pytest python3-numpy python3-scipy python3-yaml python3-matplotlib \
      python3-colcon-common-extensions \
      mesa-utils libgl1-mesa-dri libegl1 libglx-mesa0 libvulkan1 \
      x11-utils x11-apps xdotool imagemagick xvfb \
      iproute2 less procps \
    && rm -rf /var/lib/apt/lists/*

# The libraries the lablaptop gets from `tools/lab_setup.sh --pip` (not in apt at a usable version).
RUN pip install --break-system-packages --no-cache-dir shapely pymap3d websockets jsonschema

# Ubuntu 24.04 images ship user `ubuntu` with uid 1000, the same uid as the host user, so files
# written to the mounted repo keep the right owner. Pre-create the volume mount points with that owner.
RUN mkdir -p /home/ubuntu/turtlebot3_ws /home/ubuntu/plumetrace_ws /home/ubuntu/plumetrace_runs \
    && chown -R ubuntu:ubuntu /home/ubuntu
USER ubuntu
ENV HOME=/home/ubuntu
WORKDIR /home/ubuntu/lab_turtlebot
CMD ["sleep", "infinity"]
