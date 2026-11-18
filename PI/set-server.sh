#!/bin/bash
# Run as the user who installed the camera service.
set -euo pipefail

server="${1:-}"
if [[ ! "$server" =~ ^http://[a-zA-Z0-9.-]+:5001/?$ ]]; then
    echo 'Usage: bash set-server.sh http://PC_IP:5001' >&2
    exit 1
fi
server="${server%/}"
config="$HOME/.config/follow-me-camera/camera.env"
if [[ ! -f "$config" ]]; then
    echo 'Camera service is not configured. Run install.sh first.' >&2
    exit 1
fi

if ! /usr/bin/python3 - "$server" <<'PY'
import json
import sys
from urllib.request import urlopen

with urlopen(sys.argv[1] + "/api/camera/clock", timeout=5) as response:
    clock = json.load(response)
if not isinstance(clock.get("clock_id"), str):
    raise ValueError("Invalid Follow Me clock response")
PY
then
    echo "Could not reach the Follow Me server at $server." >&2
    exit 1
fi

printf 'SERVER_URL=%s\n' "$server" > "$config.tmp"
mv -- "$config.tmp" "$config"
systemctl --user restart follow-me-camera.service
echo "Camera service restarted with $server."
