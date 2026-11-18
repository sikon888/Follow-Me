# Raspberry Pi camera and skeleton setup

Hardware: Raspberry Pi 4 Model B Rev 1.5, Camera V2 (IMX219), 64-bit
Raspberry Pi OS / Debian 13 Trixie, OS Python 3.13.5.
The Pi captures images and detects skeletons. The PC runs Flask, reference
extraction, normalization and pose comparison. The browser draws paired images
and skeletons, recognizes the start gesture and awards points.

## Connection

Connect both devices to the same LAN (`rung_AIS_2.4GHz` in this installation).
The Pi in this installation uses `sikon.local`. On the Windows PC that is
running Follow Me, run `ipconfig` and use the IPv4 address of its active Ethernet
or Wi-Fi adapter. DHCP addresses can change. PuTTY uses SSH port 22.

For a new Wi-Fi network, enter its password locally:

```bash
sudo nmcli --ask device wifi connect 'YOUR_SSID'
```

## Copy and install

Install and start the PC using PC/README.md first. This PI folder contains its
own pose adapter and needs no PC source files on the Pi. If you downloaded
only PI, run `bash install.sh http://PC_IP:5001` inside it on the Pi.

Start the PC server and keep it running:

```powershell
.\PC\start.cmd
```

Allow Python/TCP 5001 on your private LAN if Windows Firewall asks.
Copy only the self-contained PI folder from the repository root:

```powershell
ssh sikon@sikon.local "mkdir -p ~/follow-me-setup"
scp -r PI sikon@sikon.local:follow-me-setup/
```

Then on the Pi, as the normal login user:

```bash
cd ~/follow-me-setup
bash PI/install.sh http://PC_IP:5001
```

The installer needs internet access. It installs OS camera packages, uses uv
to install Python 3.12, creates `~/follow-me-camera/.pose-venv`, installs
MediaPipe 0.10.18 and compatible numerical packages, downloads the official
Lite model, and checks capture/inference/upload before enabling the service
at boot. Saved reference videos need no rebuild.

## Pi 4 compatibility

Tested MediaPipe 1.1.1 and 1.0.0 ARM binaries stop on this Pi 4 with
`compiled with aes enabled ... not available on this processor`. The official
MediaPipe 0.10.18 Python 3.12 ARM wheel runs on this hardware. Picamera2 stays
on `/usr/bin/python3` so its OS bindings remain compatible. `PI/pose_worker.py`
runs inference in Python 3.12, exchanging BGR frames over a local pipe.
Both camera capture and inference run on the Pi. The PC keeps MediaPipe 1.1.1
for reference extraction and legacy camera-only clients.

## Runtime behavior

Capture is 480x360 at a target 24 FPS, preserves the widest sensor field of view,
and rotates images 180 degrees for the installed camera orientation. Actual
delivery FPS depends on inference, the scene and Wi-Fi. Every ten seconds,
the service logs delivered FPS and average inference milliseconds per frame.

The VIDEO-mode detector is reused. Each upload contains a JPEG and its
COCO-17 pixel x,y,confidence pose in `X-Pose-Skeleton`, with the original
capture timestamp and clock metadata. The PC validates and stores them
atomically. The browser sends `frame_id`, `clock_id` and aligned song time
to the player API. The PC compares that exact retained pose without running
inference or receiving the JPEG again.

Missing-person detections send an all-zero pose. Frames are not queued while
inference/upload is running. Frames expire three seconds after capture;
the browser rejects scoring results over one second old and preserves
pause/seek/restart boundaries. See [camera timing](../PC/CAMERA_TIMING.md).
The game's delay label shows `Pose: Pi` for local Pi inference.

Verified on 2026-11-12: real capture/inference/upload passed; a known dancer
image produced 17 visible joints. Live delivery measured roughly 5-6 FPS;
a five-second PC sample averaged 301 ms frame age (604 ms maximum). Service
startup is enabled with user lingering and had no restarts during verification.
Full human gameplay and Lite-versus-Full accuracy still need hands-on checking.

## Diagnose or change settings

```bash
systemctl --user status follow-me-camera --no-pager
journalctl --user -u follow-me-camera -n 30 --no-pager
curl --fail --max-time 5 http://PC_IP:5001/api/camera/clock
rpicam-hello --list-cameras
```

Replace `PC_IP` with the current Windows PC address. If the clock request
times out, check that the PC server is running, both devices are on the same
LAN and the Windows firewall allows inbound TCP 5001 on the Private profile.
On a trusted Wi-Fi network configured as Private, you can limit that rule
to the Pi's IPv4 address. Run this once in Windows PowerShell as Administrator,
replacing both example IPs with the current addresses:

```powershell
New-NetFirewallRule -DisplayName 'Follow Me camera from Pi' -Direction Inbound -Action Allow `
    -Protocol TCP -LocalPort 5001 -LocalAddress 192.168.1.20 `
    -RemoteAddress 192.168.1.21 -Profile Private
```

When switching PCs or changing addresses, run the following from your copy of
the setup folder. It checks the new address, saves it and restarts the existing
camera service using the packages already installed.

```bash
bash PI/set-server.sh http://PC_IP:5001
```

If the script has already been copied into the camera installation, run
`bash ~/follow-me-camera/set-server.sh http://PC_IP:5001`. After it restarts the
service, open `http://127.0.0.1:5001/api/camera/status` on the PC. A response
of `{"connected":true}` confirms that the server is receiving recent camera
frames.

For a manual check, stop the service so the camera is free:

```bash
systemctl --user stop follow-me-camera
python3 ~/follow-me-camera/pi_camera.py --server http://PC_IP:5001 --check
systemctl --user start follow-me-camera
```

Options: `--size 320x240|480x360|640x480`, `--fps` up to 30,
`--model PATH`, and `--pose-python PATH`. `--camera-only` reverts live
inference to the PC. Old camera-only senders remain compatible.
Stop automatic capture with `systemctl --user disable --now follow-me-camera`.

Images and recent skeletons stay in PC memory. Endpoints have no authentication;
use them only on your trusted LAN. Power off before reseating camera cables.
Use the current camera stack, not the legacy camera stack.

Official sources:

- [MediaPipe Pi example](https://github.com/google-ai-edge/mediapipe-samples/tree/main/examples/pose_landmarker/raspberry_pi)
- [MediaPipe 0.10.18 files](https://pypi.org/project/mediapipe/0.10.18/#files)
- [Picamera2 manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
