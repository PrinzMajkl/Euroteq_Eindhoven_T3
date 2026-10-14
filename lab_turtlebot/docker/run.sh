#!/usr/bin/env bash
# Jazzy container for the development laptop (the lablaptop runs everything natively and never needs this).
#   docker/run.sh image          build the image plumetrace-jazzy from docker/Dockerfile
#   docker/run.sh up             start the container (GPU, X11 windows, ports 8090 and 8765 on 127.0.0.1)
#   docker/run.sh ws             build the ROBOTIS underlay and plumetrace inside the container
#   docker/run.sh x <command>    run a command inside it with config/env.sh sourced (bash -lc)
#   docker/run.sh sh             interactive shell with config/env.sh sourced
#   docker/run.sh down           stop and remove the container (the build volumes stay)
# Graphics: PLUMETRACE_GFX=nvidia (default) | intel (/dev/dri) | software (llvmpipe).
# Nothing is written to this repo's build/, install/ or log/: the two workspaces live in Docker volumes
# (plumetrace_tb3_ws -> ~/turtlebot3_ws, plumetrace_ws -> ~/plumetrace_ws); run folders go to docker/runs/.
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE=plumetrace-jazzy:latest
NAME=plumetrace-jazzy
IN=/home/ubuntu/lab_turtlebot
ENVSH="source $IN/src/plumetrace/config/env.sh"

case "${1:-}" in
  image)
    docker build -t "$IMAGE" "$REPO/docker" ;;
  up)
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    mkdir -p "$REPO/docker/runs"
    gfx=()
    case "${PLUMETRACE_GFX:-nvidia}" in
      nvidia)   gfx=(--device nvidia.com/gpu=all -e NVIDIA_DRIVER_CAPABILITIES=all
                     -e __NV_PRIME_RENDER_OFFLOAD=1 -e __GLX_VENDOR_LIBRARY_NAME=nvidia) ;;
      intel)    gfx=(--device /dev/dri) ;;
      software) gfx=(-e LIBGL_ALWAYS_SOFTWARE=1) ;;
    esac
    disp=()
    if [ -n "${DISPLAY:-}" ] && [ -S "/tmp/.X11-unix/X${DISPLAY#:}" ]; then
      # a copy of the X cookie that is valid from any hostname (the container's differs from the host's)
      xa="$REPO/docker/runs/.xauth"; : > "$xa"; chmod 600 "$xa"
      xauth nlist "$DISPLAY" 2>/dev/null | sed -e 's/^..../ffff/' | xauth -f "$xa" nmerge - 2>/dev/null || true
      disp=(-e "DISPLAY=$DISPLAY" -e XAUTHORITY=/tmp/.xauth -e QT_X11_NO_MITSHM=1
            -v /tmp/.X11-unix:/tmp/.X11-unix -v "$xa:/tmp/.xauth:ro")
    else
      echo "no X display reachable: start launches with gui:=false rviz:=false headless_rendering:=true"
    fi
    docker run -d --name "$NAME" "${gfx[@]}" "${disp[@]}" \
      -e PLUMETRACE_WS=/home/ubuntu/plumetrace_ws -e ROS_DOMAIN_ID=32 \
      -v "$REPO:$IN" \
      -v plumetrace_tb3_ws:/home/ubuntu/turtlebot3_ws -v plumetrace_ws:/home/ubuntu/plumetrace_ws \
      -v "$REPO/docker/runs:/home/ubuntu/plumetrace_runs" \
      -p 127.0.0.1:8090:8090 -p 127.0.0.1:8765:8765 \
      --shm-size 1g "$IMAGE" sleep infinity ;;
  ws)
    docker exec "$NAME" bash -lc "$IN/docker/build_ws.sh" ;;
  x)
    shift; docker exec "$NAME" bash -lc "$ENVSH && cd $IN/src/plumetrace && $*" ;;
  sh)
    docker exec -it "$NAME" bash -lc "$ENVSH && cd $IN/src/plumetrace && exec bash" ;;
  down)
    docker rm -f "$NAME" ;;
  *)
    sed -n '2,11p' "${BASH_SOURCE[0]}"; exit 1 ;;
esac
