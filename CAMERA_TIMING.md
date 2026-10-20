# Camera capture timing

Copy the updated `pi_camera.py` to the Raspberry Pi, stop its old process with
Ctrl+C, and restart it:

```bash
python3 pi_camera.py --server http://192.168.1.105:5001
```

Use the PC's current local address if it changes. Refresh the game page too.
No reference rebuild is needed for this timing update.

The script samples `/api/camera/clock` three times and uses the lowest round-trip
sample to estimate its monotonic clock offset. It resynchronizes every 30 seconds.
Each JPEG includes its capture timestamp mapped into the server clock, the server
clock identifier, and the estimated clock uncertainty. A server restart changes
the identifier, triggering resynchronization instead of using an obsolete offset.

Image and metadata come from the same Picamera2 request. `SensorTimestamp` marks
the first pixel's sensor readout, so half of `ExposureTime` is subtracted to
approximate that row's exposure midpoint. This is an approximation for a rolling
shutter image, not a single exact exposure instant for every pixel. See the
[official Picamera2 manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf).
Missing or implausible metadata uses capture-completion time and is marked estimated.

The server retains that timestamp with the JPEG and returns it with the server's
current time. The browser estimates image age, adding half of its fetch round trip
for the return transfer. It subtracts this age, scaled by playback rate, from the
song's playback time before submitting the image for detection and scoring. Model
processing cannot shift the reference selection to a later song time.

Playback boundaries prevent frames captured before start, resume, seek, buffering,
or a speed change from scoring in a new playback segment. Results more than one
second after capture are skipped. Camera connection expires three seconds after
capture. These limits favor fresh feedback rather than scoring very old images.

The player panel shows estimated camera-to-result delay in milliseconds. With an
old Pi script, uploads remain compatible but timing starts at server receipt;
the panel asks for a script update because upstream delay is unknown. Update the
script for full capture alignment. Clock and Wi-Fi asymmetry can still introduce
error, so verify alignment on real Pi hardware and the actual network.
