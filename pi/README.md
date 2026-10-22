# Raspberry Pi camera setup

Use Raspberry Pi OS with a CSI ribbon camera supported by Picamera2.
Power off the Pi before connecting or reseating the camera cable. Pi 5 and
Pi Zero use a different camera connector/cable from a standard Pi 4.

## Network

Connect the Pi to `rung_AIS_2.4GHz`. With NetworkManager, this prompts for
the Wi-Fi password locally (do not send the password in chat):

```bash
sudo nmcli --ask device wifi connect 'rung_AIS_2.4GHz'
hostname -I
whoami
```

The PC's Wi-Fi address during installation was `192.168.1.114`.
The Pi was reachable as `sikon.local` at `192.168.1.115`.
Both devices must connect to the same router/LAN. IP addresses can change;
verify with `ipconfig` on the PC. Guest Wi-Fi/client isolation can block access.

## Copy from Windows

Enable SSH on the Pi using Raspberry Pi Configuration or `sudo raspi-config`.
Replace `USERNAME` and `PI_IP` below with the Pi login and address:

```powershell
ssh USERNAME@PI_IP "mkdir -p ~/follow-me-setup"
scp pi_camera.py USERNAME@PI_IP:follow-me-setup/
scp -r pi USERNAME@PI_IP:follow-me-setup/
```

Start the PC server from this project and leave it running:

```powershell
.\.venv\Scripts\python.exe app.py
```

Allow TCP port 5001/Python on the trusted local network if Windows Firewall
blocks the connection. The Pi does not need the PC requirements.txt, model,
MediaPipe or the full repository.

## Install and start on the Pi

```bash
cd ~/follow-me-setup
bash pi/install.sh http://192.168.1.114:5001
```

This installs OS camera packages, checks clock sync, captures and uploads a
JPEG, and then enables a user service at boot. A failed check stops installation
before enabling the service. No Wi-Fi password is stored in project files.

Capture defaults to 480x360 at a target 24 FPS, with 180-degree rotation for the
installed camera orientation. The browser scales the preview to fit its panel.
Sensor mode selection preserves the widest available field of view rather than
using a cropped sensor mode for small output sizes.
Manual runs support `--size 320x240`, `--size 480x360`, or `--size 640x480`
and `--fps` up to 30. PC pose inference also limits skeleton update rate.

## Diagnose or change settings

```bash
rpicam-hello --list-cameras
curl --fail http://192.168.1.114:5001/api/camera/clock
journalctl --user -u follow-me-camera -n 50 --no-pager
systemctl --user status follow-me-camera
```

Open the game on the PC; its Ready page should show the Pi camera. If the camera
is missing from the camera list, check its cable, connector and OS camera support.
Do not enable the legacy camera stack. Close other camera apps before starting.

To change the server address, edit `~/.config/follow-me-camera/camera.env`, then
run `systemctl --user restart follow-me-camera`. To stop automatic capture:

```bash
systemctl --user disable --now follow-me-camera
```

For a manual check, stop the service first so the camera is free:

```bash
systemctl --user stop follow-me-camera
python3 ~/follow-me-camera/pi_camera.py --server http://192.168.1.114:5001 --check
systemctl --user start follow-me-camera
```

Camera frames stay in PC memory. Use this unauthenticated endpoint only on your
trusted LAN. Official setup references:
https://github.com/raspberrypi/picamera2 and
https://www.raspberrypi.com/documentation/computers/camera_software.html
