#!/bin/bash
# Run as your normal Pi user: bash pi/install.sh http://PC_IP:5001
set -euo pipefail
server="${1:-}"
if [[ ! "$server" =~ ^http://[a-zA-Z0-9.-]+:5001/?$ ]]; then
    echo 'Usage: bash pi/install.sh http://PC_IP:5001' >&2
    exit 1
fi
if [[ "$EUID" -eq 0 ]]; then
    echo 'Run as your normal Pi login user, without sudo.' >&2
    exit 1
fi
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
target_dir="$HOME/follow-me-camera"
sudo apt-get update
sudo apt-get install -y python3-picamera2 python3-opencv rpicam-apps
mkdir -p "$target_dir" "$HOME/.config/follow-me-camera" "$HOME/.config/systemd/user"
if [[ "$source_dir/pi_camera.py" != "$target_dir/pi_camera.py" ]]; then
    install -m 644 "$source_dir/pi_camera.py" "$target_dir/pi_camera.py"
fi
printf 'SERVER_URL=%s\n' "${server%/}" > "$HOME/.config/follow-me-camera/camera.env"
install -m 644 "$source_dir/pi/follow-me-camera.service" "$HOME/.config/systemd/user/follow-me-camera.service"
systemctl --user daemon-reload
echo 'Checking camera and PC connection before enabling startup...'
/usr/bin/python3 "$target_dir/pi_camera.py" --server "${server%/}" --check
sudo loginctl enable-linger "$USER"
systemctl --user enable --now follow-me-camera.service
systemctl --user restart follow-me-camera.service
echo 'Installed. Logs: journalctl --user -u follow-me-camera -f'
