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
let total = 0, latestAccuracy = 0, accuracySum = 0, scoredSamples = 0, matchedSamples = 0;
let nextScoreAt = 3;

function isScoreCheckpoint(seconds) {
    if (!Number.isFinite(seconds) || seconds < nextScoreAt) return false;
    // Skip missed checkpoints rather than awarding a burst of catch-up points.
    nextScoreAt = (Math.floor(seconds / 3) + 1) * 3;
    return true;
}
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
    const visible = index => pose[index]?.[2] >= 0.3 &&
        pose[index].every(Number.isFinite);
    // COCO-17: nose 0, shoulders 5/6, wrists 9/10. Pixel y increases downwards.
    const raised = visible(0) && [9, 10].some(wrist =>
        visible(wrist) &&
        pose[wrist][1] < pose[0][1] -
            Math.max(2, piPreview.height * 0.01));
    if (!raised) {
        resetStartGesture();
        gestureLatched = false;
        playerPoseStatus.textContent = !visible(0)
            ? 'Head not detected: face the camera'
            : ![9, 10].some(visible)
                ? 'Hand not detected: keep either wrist in view'
                : 'Hand detected: raise it higher than your nose; hold for 2.0 s';
        return;
    }
    if (gestureLatched) return;
    if (lastGestureSample === null || now - lastGestureSample > 3000) {
        resetStartGesture();
        handRaisedSince = now;
    }
    lastGestureSample = now;
    gestureSamples++;
    const remaining = Math.max(0, 2000 - (now - handRaisedSince)) / 1000;
    playerPoseStatus.textContent = remaining > 0
        ? 'Hand raised: hold for ' + remaining.toFixed(1) + ' s more'
        : 'Hand raised: confirming...';
    if (now - handRaisedSince >= 2000 && gestureSamples >= 3) {
        gestureLatched = true;
        resetStartGesture();
        clearPlayerScore();
        startCountdown();
    }
}

function clearPlayerScore() {
    generation++;
    total = latestAccuracy = accuracySum = scoredSamples = matchedSamples = 0;
    nextScoreAt = 3;
    document.getElementById('gameSummary').hidden = true;
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
video.addEventListener('ended', () => {
    generation++;
    document.getElementById('finalScore').textContent = Math.round(total).toLocaleString();
    document.getElementById('finalAccuracy').textContent = scoredSamples
        ? `${Math.round(accuracySum / scoredSamples)}%` : 'No scored poses';
    document.getElementById('finalMatches').textContent = `${matchedSamples} / ${scoredSamples}`;
    document.getElementById('finalFeedback').textContent = scoredSamples
        ? 'Checked every 3 seconds: up to 40 points for an easy hand match and 60 for a close body match.'
        : 'No poses were scored. Check camera visibility and delay, then try again.';
    document.getElementById('gameSummary').hidden = false;
});

function setPiConnected(connected) {
    piConnection.textContent = connected ? 'Connected' : 'Disconnected';
    piConnection.classList.toggle('connected', connected);
    piPreview.hidden = !connected;
    piDisconnected.hidden = connected;
    if (!connected) {
        resetStartGesture();
        if (wasConnected) {
            generation++;
            latestAccuracy = 0;
            updateScoreboard(total, latestAccuracy);
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
    let retryDelay = 33;
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
        // Draw the image and its overlays together, after inference finishes.
        // Clearing the canvas before awaiting inference caused visible blinking.
        if (piPreview.width !== bitmap.width) piPreview.width = bitmap.width;
        if (piPreview.height !== bitmap.height) piPreview.height = bitmap.height;
        piContext.drawImage(bitmap, 0, 0);
        drawPlayerSkeleton(result.skeleton);
        const clearPose = [5, 6, 9, 10, 11, 12, 15, 16].every(index =>
            result.skeleton[index]?.[2] >= 0.3 && result.skeleton[index].every(Number.isFinite));
        const notice = document.getElementById('playerTrackingNotice');
        notice.hidden = gameRunning || countdownRunning || video.ended || clearPose;
        notice.textContent = 'Skeleton unclear: step back and keep your whole body in view';
        playerPoseStatus.textContent = result.detected ? 'Player detected' : 'Stand back so your full body is visible';
        // Gesture recognition allows inference delay; scoring stays strict.
        if (token === generation && timing && timing.ageMs <= MAX_SCORE_FRAME_AGE_MS &&
            resultAgeMs <= 3000) updateStartGesture(result.skeleton);
        else if (!gameRunning && !countdownRunning) {
            resetStartGesture();
            playerPoseStatus.textContent = 'Camera delayed; waiting for a fresh frame';
        }
        if (resultAgeMs > MAX_SCORE_FRAME_AGE_MS) {
            if (gameRunning) playerPoseStatus.textContent = 'Camera delayed; waiting for a fresh frame';
            return;
        }
        if (token !== generation || !scoring || !gameRunning || video.paused || video.seeking) return;
        if (result.accuracy === null) {
            gameStatus.textContent = 'Reference pose unavailable';
            return;
        }
        if (!isScoreCheckpoint(songTime)) return;
        latestAccuracy = result.accuracy;
        accuracySum += result.accuracy;
        scoredSamples++;
        if (result.accuracy >= 70) matchedSamples++;
        total += Math.round(result.accuracy);
        updateScoreboard(total, latestAccuracy);
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
