// The Pi pushes JPEGs to Flask. Score exactly the image shown in the player panel.
const playerEndpoint = document.currentScript.dataset.endpoint;
const piPreview = document.getElementById('piPreview');
const piContext = piPreview.getContext('2d');
const piConnection = document.getElementById('piConnection');
const piDisconnected = document.getElementById('piDisconnected');
const playerPoseStatus = document.getElementById('playerPoseStatus');
const cameraTimingStatus = document.getElementById('cameraTimingStatus');
const playerEdges = [[0,1],[0,2],[1,3],[2,4],[5,6],[5,7],[7,9],
    [6,8],[8,10],[5,11],[6,12],[11,12],[11,13],[13,15],[12,14],[14,16]];
let generation = 0, lastFrameId = null, wasConnected = false;
let total = 0, latestAccuracy = 0, combo = 0;
let handRaisedSince = null, lastGestureSample = null, gestureSamples = 0;
let gestureLatched = false;
let playbackSegmentStart = Infinity;
const MAX_SCORE_FRAME_AGE_MS = 1000;

// Both response timestamps use the server's monotonic clock. Half the browser
// round trip estimates the remaining transfer delay, without wall-clock sync.
function cameraFrameTiming(headers, roundTripMs) {
    const capturedHeader = headers.get('X-Captured-At');
    const serverHeader = headers.get('X-Server-Time');
    if (capturedHeader === null || serverHeader === null) return null;
    const captured = Number(capturedHeader), server = Number(serverHeader);
    const uncertainty = Number(headers.get('X-Clock-Uncertainty') || 0);
    if (![captured, server, uncertainty, roundTripMs].every(Number.isFinite) ||
        uncertainty < 0 || uncertainty > 0.25 || roundTripMs < 0 ||
        captured > server + uncertainty + 0.05) return null;
    return {
        ageMs: Math.max(0, (server - captured) * 1000 + roundTripMs / 2),
        source: headers.get('X-Timing-Source'),
    };
}

function alignedSongTime(songTime, ageMs, playbackRate, observedAt, segmentStart) {
    if (!Number.isFinite(ageMs) || ageMs < 0 || ageMs > MAX_SCORE_FRAME_AGE_MS ||
        observedAt - ageMs < segmentStart) return null;
    const aligned = songTime - ageMs / 1000 * playbackRate;
    return aligned >= 0 ? aligned : null;
}

function beginPlaybackSegment() { playbackSegmentStart = performance.now(); }
video.addEventListener('playing', beginPlaybackSegment);
video.addEventListener('waiting', () => { playbackSegmentStart = Infinity; generation++; });
video.addEventListener('seeked', () => {
    if (!video.paused) beginPlaybackSegment();
});
video.addEventListener('ratechange', () => {
    generation++;
    if (!video.paused) beginPlaybackSegment();
});

function resetStartGesture() {
    handRaisedSince = lastGestureSample = null;
    gestureSamples = 0;
}

function updateStartGesture(pose, now = performance.now()) {
    if (gameRunning || countdownRunning) {
        resetStartGesture();
        return;
    }
    const visible = index => pose[index]?.[2] >= 0.5;
    // COCO-17: nose 0, shoulders 5/6, wrists 9/10. Pixel y increases downwards.
    const raised = visible(0) && visible(5) && visible(6) &&
        [9, 10].some(index => visible(index) && pose[index][1] <
            Math.min(pose[0][1], pose[5][1], pose[6][1]) -
            Math.max(5, Math.abs(pose[5][0] - pose[6][0]) * 0.1));
    if (!raised) {
        resetStartGesture();
        gestureLatched = false;
        playerPoseStatus.textContent = 'Raise either hand above your head for 1 second to start';
        return;
    }
    if (gestureLatched) return;
    if (lastGestureSample === null || now - lastGestureSample > 2000) {
        resetStartGesture();
        handRaisedSince = now;
    }
    lastGestureSample = now;
    gestureSamples++;
    playerPoseStatus.textContent = 'Hold your hand up to start…';
    if (now - handRaisedSince >= 1000 && gestureSamples >= 3) {
        gestureLatched = true;
        resetStartGesture();
        clearPlayerScore();
        startCountdown();
    }
}

function clearPlayerScore() {
    generation++;
    total = latestAccuracy = combo = 0;
    resetScoreboard();
}
readyButton.addEventListener('click', () => {
    if (!gameRunning && !countdownRunning) clearPlayerScore();
}, true);
restartButton.addEventListener('click', () => {
    clearPlayerScore();
    resetStartGesture();
}, true);
video.addEventListener('seeking', () => { playbackSegmentStart = Infinity; clearPlayerScore(); });
video.addEventListener('pause', () => { playbackSegmentStart = Infinity; generation++; });

function setPiConnected(connected) {
    piConnection.textContent = connected ? 'Connected' : 'Disconnected';
    piConnection.classList.toggle('connected', connected);
    piPreview.hidden = !connected;
    piDisconnected.hidden = connected;
    if (!connected) {
        resetStartGesture();
        if (wasConnected) {
            generation++;
            combo = 0;
            latestAccuracy = 0;
            updateScoreboard(total, latestAccuracy, combo);
        }
        lastFrameId = null;
        cameraTimingStatus.textContent = '';
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
    const pollStarted = performance.now();
    let retryDelay = 100;
    try {
        const fetchStarted = performance.now();
        const response = await fetch('/api/camera/frame', {
            cache: 'no-store', signal: AbortSignal.timeout(2500)});
        const observedAt = performance.now();
        if (!response.ok) { retryDelay = 500; setPiConnected(false); return; }
        setPiConnected(true);
        const frameId = response.headers.get('X-Frame-Id');
        if (frameId === lastFrameId) return;
        lastFrameId = frameId;
        const token = generation;
        const timing = cameraFrameTiming(response.headers, observedAt - fetchStarted);
        const songTime = timing ? alignedSongTime(video.currentTime, timing.ageMs,
            video.playbackRate, observedAt, playbackSegmentStart) : null;
        const scoring = songTime !== null && gameRunning && !video.paused && !video.seeking && !video.ended;
        const blob = await response.blob();
        bitmap = await createImageBitmap(blob);
        piPreview.width = bitmap.width;
        piPreview.height = bitmap.height;
        piContext.drawImage(bitmap, 0, 0);
        const form = new FormData();
        form.append('frame', blob, 'pi-camera.jpg');
        form.append('time', songTime ?? Math.max(0, video.currentTime));
        const resultResponse = await fetch(playerEndpoint, {
            method: 'POST', body: form, signal: AbortSignal.timeout(5000)});
        const result = await resultResponse.json();
        if (!resultResponse.ok) throw new Error(result.error || 'Pose detection failed');
        // Render scores immediately. Timestamp age already guards freshness;
        // an extra status request would only postpone the scoreboard update.
        const resultAgeMs = timing ? timing.ageMs + performance.now() - observedAt : Infinity;
        cameraTimingStatus.textContent = timing
            ? `Camera delay: ${Math.round(resultAgeMs)} ms${timing.source === 'sensor' ? '' : ' (estimated; update Pi camera script)'}`
            : 'Camera timing unavailable; scoring is waiting';
        drawPlayerSkeleton(result.skeleton);
        playerPoseStatus.textContent = result.detected ? 'Player detected' : 'Stand back so your full body is visible';
        if (resultAgeMs > MAX_SCORE_FRAME_AGE_MS) {
            resetStartGesture();
            playerPoseStatus.textContent = 'Camera delayed; waiting for a fresh frame';
            return;
        }
        if (token === generation) updateStartGesture(result.skeleton);
        if (token !== generation || !scoring || !gameRunning || video.paused || video.seeking) return;
        if (result.accuracy === null) {
            gameStatus.textContent = 'Reference pose unavailable';
            return;
        }
        latestAccuracy = result.accuracy;
        combo = result.accuracy >= 70 ? combo + 1 : 0;
        total += Math.round(result.accuracy);
        updateScoreboard(total, latestAccuracy, combo);
        gameStatus.textContent = result.detected ? 'Dancing' : 'Player not detected';
    } catch (error) {
        retryDelay = 500;
        resetStartGesture();
        // Pose errors do not imply that the camera has disconnected.
        if (bitmap) playerPoseStatus.textContent = error.message;
        else setPiConnected(false);
    } finally {
        bitmap?.close();
        // One request at a time, without adding a fixed pause after inference.
        setTimeout(pollPiCamera, Math.max(0, retryDelay - (performance.now() - pollStarted)));
    }
}
setPiConnected(false);
pollPiCamera();
