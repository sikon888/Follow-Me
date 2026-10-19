// The Pi pushes JPEGs to Flask. Score exactly the image shown in the player panel.
const playerEndpoint = document.currentScript.dataset.endpoint;
const piPreview = document.getElementById('piPreview');
const piContext = piPreview.getContext('2d');
const piConnection = document.getElementById('piConnection');
const piDisconnected = document.getElementById('piDisconnected');
const playerPoseStatus = document.getElementById('playerPoseStatus');
const playerEdges = [[0,1],[0,2],[1,3],[2,4],[5,6],[5,7],[7,9],
    [6,8],[8,10],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16]];
let generation = 0, lastFrameId = null, wasConnected = false;
let total = 0, samples = 0, accuracySum = 0, combo = 0;

function clearPlayerScore() {
    generation++;
    total = samples = accuracySum = combo = 0;
    resetScoreboard();
}
readyButton.addEventListener('click', () => {
    if (!gameRunning && !countdownRunning) clearPlayerScore();
}, true);
restartButton.addEventListener('click', clearPlayerScore, true);
video.addEventListener('seeking', clearPlayerScore);
video.addEventListener('pause', () => { generation++; });

function setPiConnected(connected) {
    piConnection.textContent = connected ? 'Connected' : 'Disconnected';
    piConnection.classList.toggle('connected', connected);
    piPreview.hidden = !connected;
    piDisconnected.hidden = connected;
    if (!connected) {
        if (wasConnected) {
            generation++;
            combo = 0;
            updateScoreboard(total, samples ? accuracySum / samples : 0, combo);
        }
        lastFrameId = null;
        playerPoseStatus.textContent = 'Waiting for Raspberry Pi camera';
    }
    wasConnected = connected;
}

function drawPlayerSkeleton(pose) {
    piContext.strokeStyle = '#54ffb0';
    piContext.fillStyle = '#fff';
    piContext.lineWidth = 3;
    const valid = index => pose[index][2] >= 0.3;
    for (const [a, b] of playerEdges) {
        if (!valid(a) || !valid(b)) continue;
        piContext.beginPath();
        piContext.moveTo(pose[a][0], pose[a][1]);
        piContext.lineTo(pose[b][0], pose[b][1]);
        piContext.stroke();
    }
    pose.forEach((point, index) => {
        if (!valid(index)) return;
        piContext.beginPath();
        piContext.arc(point[0], point[1], 4, 0, Math.PI * 2);
        piContext.fill();
    });
}

async function pollPiCamera() {
    let bitmap;
    try {
        const response = await fetch('/api/camera/frame', {
            cache: 'no-store', signal: AbortSignal.timeout(2500)});
        if (!response.ok) { setPiConnected(false); return; }
        setPiConnected(true);
        const frameId = response.headers.get('X-Frame-Id');
        if (frameId === lastFrameId) return;
        lastFrameId = frameId;
        const token = generation;
        const songTime = video.currentTime;
        const scoring = gameRunning && !video.paused && !video.seeking && !video.ended;
        const blob = await response.blob();
        bitmap = await createImageBitmap(blob);
        piPreview.width = bitmap.width;
        piPreview.height = bitmap.height;
        piContext.drawImage(bitmap, 0, 0);
        const form = new FormData();
        form.append('frame', blob, 'pi-camera.jpg');
        form.append('time', songTime);
        const resultResponse = await fetch(playerEndpoint, {
            method: 'POST', body: form, signal: AbortSignal.timeout(5000)});
        const result = await resultResponse.json();
        if (!resultResponse.ok) throw new Error(result.error || 'Pose detection failed');
        // Recheck freshness after inference, which can take longer on a slow PC.
        const statusResponse = await fetch('/api/camera/status', {signal: AbortSignal.timeout(2500)});
        if (!statusResponse.ok) throw new Error('Cannot check camera connection');
        const status = await statusResponse.json();
        if (!status.connected) { setPiConnected(false); return; }
        drawPlayerSkeleton(result.skeleton);
        playerPoseStatus.textContent = result.detected ? 'Player detected' : 'Stand back so your full body is visible';
        if (token !== generation || !scoring || !gameRunning || video.paused || video.seeking) return;
        if (result.accuracy === null) {
            gameStatus.textContent = 'Reference pose unavailable';
            return;
        }
        samples++;
        accuracySum += result.accuracy;
        combo = result.accuracy >= 70 ? combo + 1 : 0;
        total += Math.round(result.accuracy);
        updateScoreboard(total, accuracySum / samples, combo);
        gameStatus.textContent = result.detected ? 'Dancing' : 'Player not detected';
    } catch (error) {
        // Pose errors do not imply that the camera has disconnected.
        if (bitmap) playerPoseStatus.textContent = error.message;
        else setPiConnected(false);
    } finally {
        bitmap?.close();
        setTimeout(pollPiCamera, 150);
    }
}
setPiConnected(false);
pollPiCamera();
