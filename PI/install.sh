#!/bin/bash
# Run as your normal Pi user: bash PI/install.sh http://PC_IP:5001
set -euo pipefail
server="${1:-}"
if [[ ! "$server" =~ ^http://[a-zA-Z0-9.-]+:5001/?$ ]]; then
    echo 'Usage: bash PI/install.sh http://PC_IP:5001' >&2
    exit 1
fi
if [[ "$EUID" -eq 0 ]]; then
    echo 'Run as your normal Pi login user, without sudo.' >&2
    exit 1
fi
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
target_dir="$HOME/follow-me-camera"
sudo apt-get update
sudo apt-get install -y python3-picamera2 python3-opencv python3-venv rpicam-apps
mkdir -p "$target_dir" "$HOME/.config/follow-me-camera" "$HOME/.config/systemd/user"
mkdir -p "$target_dir/modules" "$target_dir/models"
if [[ "$source_dir/pi_camera.py" != "$target_dir/pi_camera.py" ]]; then
    install -m 644 "$source_dir/pi_camera.py" "$target_dir/pi_camera.py"
fi
for file in __init__.py pose_processor.py; do
    if [[ "$source_dir/modules/$file" != "$target_dir/modules/$file" ]]; then
        install -m 644 "$source_dir/modules/$file" "$target_dir/modules/$file"
    fi
done
if [[ "$source_dir/pose_worker.py" != "$target_dir/pose_worker.py" ]]; then
    install -m 644 "$source_dir/pose_worker.py" "$target_dir/pose_worker.py"
fi
python3 -m venv --system-site-packages "$target_dir/.venv"
# Current MediaPipe ARM wheels require AES, which the Pi 4 CPU lacks. Keep
# Picamera2 on OS Python and use the older official ARM wheel in a worker.
"$target_dir/.venv/bin/python" -m pip install --only-binary=:all: uv
"$target_dir/.venv/bin/uv" --no-progress python install 3.12
if [[ ! -x "$target_dir/.pose-venv/bin/python" ]]; then
    "$target_dir/.venv/bin/uv" venv --python 3.12 "$target_dir/.pose-venv"
fi
"$target_dir/.venv/bin/uv" --no-progress pip install --python "$target_dir/.pose-venv/bin/python" \
    'mediapipe==0.10.18' 'numpy<2' 'opencv-contrib-python<4.12' 'jax==0.4.35' 'jaxlib==0.4.35'
python3 -c 'import cv2, picamera2'
if [[ ! -s "$target_dir/models/pose_landmarker_lite.task" ]]; then
    "$target_dir/.venv/bin/python" -c 'import sys, urllib.request; urllib.request.urlretrieve("https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task", sys.argv[1])' "$target_dir/models/pose_landmarker_lite.task"
fi
echo 'Checking camera and PC connection before enabling startup...'
was_active=false
if systemctl --user is-active --quiet follow-me-camera.service; then
    was_active=true
    systemctl --user stop follow-me-camera.service
fi
trap 'if $was_active; then systemctl --user start follow-me-camera.service; fi' EXIT
python3 "$target_dir/pi_camera.py" --server "${server%/}" --check
printf 'SERVER_URL=%s\n' "${server%/}" > "$HOME/.config/follow-me-camera/camera.env"
install -m 644 "$source_dir/follow-me-camera.service" "$HOME/.config/systemd/user/follow-me-camera.service"
systemctl --user daemon-reload
sudo loginctl enable-linger "$USER"
systemctl --user enable --now follow-me-camera.service
systemctl --user restart follow-me-camera.service
echo 'Installed. Logs: journalctl --user -u follow-me-camera -f'
