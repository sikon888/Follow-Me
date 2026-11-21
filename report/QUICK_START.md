# Follow Me installation and play guide

Follow Me runs on a Windows PC. A Raspberry Pi with a camera sends live poses to the PC so the game can score your movements against a dance video.

## 1. Install on Windows

1. Install **Python 3.14 x64** and make it available through the Python launcher or `PATH`.
2. Download **Follow-Me-offline-Windows-x64.zip** from the [GitHub Releases page](https://github.com/sikon888/Follow-Me/releases). Extract the whole ZIP to a writable folder. The package includes the model, Windows dependencies, and six songs with saved pose references.
3. Double-click `PC\start.cmd`. Wait for first-run setup to finish, then leave the server window open.
4. Open `http://127.0.0.1:5001` in a browser on the PC.

If the release ZIP is unavailable, install Git and Git LFS and run the commands below. The first launch from a clone needs internet access to install the Windows dependencies. [PC setup details](../PC/README.md)

```powershell
git lfs install
git clone https://github.com/sikon888/Follow-Me.git
cd Follow-Me
git lfs pull
.\PC\start.cmd
```

## 2. Connect the Raspberry Pi camera

1. Connect the PC and Pi to the same private network. The tested hardware is a Raspberry Pi 4 with Camera Module V2 and 64-bit Raspberry Pi OS (Trixie).
2. On the Windows PC, run `ipconfig` and note the IPv4 address of your active Wi-Fi or Ethernet adapter. If Windows Firewall prompts, allow network access on the private network.
3. Copy the `PI` folder to the Raspberry Pi. From the directory containing that folder on the Pi, run the following command with your PC's actual IPv4 address in place of `PC_IP`. The Pi needs internet access for the first installation.

   ```bash
   bash PI/install.sh http://PC_IP:5001
   ```

4. Open `http://127.0.0.1:5001/api/camera/status` on the PC and check that `connected` is `true`. If the PC address changes, run `bash PI/set-server.sh http://PC_IP:5001` with the new address. [Pi setup and troubleshooting](../PI/README.md)

## 3. Play a song

1. Select a saved song to open the game. For your own MP4, upload it and choose **Save Reference** before playing.
2. Stand where the camera can see your whole body. Check that the player panel shows your camera image and skeleton.
3. Raise either hand above your head for two seconds to start the countdown. Follow the dancer on screen and check your score and accuracy when the song ends.
