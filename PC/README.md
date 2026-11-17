# Follow Me - PC server

This folder contains the complete Windows PC application, model, web assets,
saved videos and pose references. No files from the repository root are needed.
Use Windows x64 with Python 3.14. The Pi camera sender is installed separately
from `PI`; the PC can start and manage reference videos without a Pi.

## Download

The videos and NPZ references use Git LFS. Install Git and Git LFS, then:

```powershell
git lfs install
git clone https://github.com/sikon888/Follow-Me.git
cd Follow-Me
git lfs pull
```

You can now copy just `PC` to another directory or computer. Download ZIP may
contain LFS pointer files instead of videos; use the clone procedure to ensure
the six saved songs and references are present. You can also use your own MP4s
through Upload and Save Reference.

## Install and run

Open PowerShell **inside this PC folder**:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5001. Allow Python/TCP 5001 on your private LAN for the Pi.
Give the Pi your PC's current LAN IPv4 address from `ipconfig`, for example
`http://192.168.1.20:5001`. Keep the server running while installing/using the Pi.
Both devices must be on the same trusted LAN; endpoints have no authentication.

The Full pose model is included in `models`. To replace a missing model:

```powershell
New-Item -ItemType Directory -Force models
Invoke-WebRequest 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task' -OutFile models/pose_landmarker_full.task
```

`MEDIAPIPE_POSE_MODEL` overrides the model path. Optional `YOUTUBE_API_KEY`
enables API search; keyless search is available. Internet access is required for
package installation and YouTube features. FFmpeg is supplied by imageio-ffmpeg.
YouTube may restrict individual downloads. Upload local MP4s as an alternative.

## Play

Select a saved song, or upload an MP4 and save its reference first. Connect the
Pi camera, stand fully in view, then raise either hand above your head for two
seconds. The browser displays the Pi's paired camera image and skeleton.
References, uploads and model paths resolve relative to this folder regardless
of the shell's working directory. Timing details: [CAMERA_TIMING.md](CAMERA_TIMING.md).

## Checks

With both downloaded folders side by side, run from inside `PC`:

```powershell
$env:PYTHONPATH = "$PWD;$PWD\..\PI"
.\.venv\Scripts\python.exe -m unittest discover -s Test -p 'test_*.py' -v
node Test/test_game_summary.cjs
node Test/test_start_gesture.cjs
node Test/test_video_autoplay.cjs
```

Node is only needed for JavaScript tests. The timing tests import the Pi sender,
so those tests require `PI`; the PC application itself does not.
