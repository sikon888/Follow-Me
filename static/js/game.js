/* =========================================
   ELEMENTS
========================================= */

const video =
    document.getElementById("referenceVideo");

const readyButton =
    document.getElementById("readyButton");



const restartButton =
    document.getElementById("restartButton");

const countdown =
    document.getElementById("countdown");

const startOverlay =
    document.getElementById("startOverlay");

const gameStatus =
    document.getElementById("gameStatus");

const videoProgress =
    document.getElementById("videoProgress");

const currentTimeText =
    document.getElementById("currentTime");

const durationText =
    document.getElementById("duration");

const volumeSlider =
    document.getElementById("volumeSlider");

const muteButton =
    document.getElementById("muteButton");

const scoreValue =
    document.getElementById("scoreValue");





/* =========================================
   GAME STATE
========================================= */

let gameRunning = false;

let countdownRunning = false;

let isPaused = false;

let previousVolume = 1;

let countdownGeneration = 0;
let countdownAudio = null;
let countdownGain = null;
const countdownVoices = new Set();

// Initialize during the Ready click so browsers allow the countdown audio.
function prepareCountdownAudio() {
    try {
        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (!AudioContextClass) return;
        if (!countdownAudio) {
            countdownAudio = new AudioContextClass();
            countdownGain = countdownAudio.createGain();
            countdownGain.connect(countdownAudio.destination);
        }
        updateCountdownVolume();
        countdownAudio.resume().catch(error => console.warn('Countdown audio:', error));
    } catch (error) {
        console.warn('Countdown audio:', error);
    }
}

function updateCountdownVolume() {
    if (countdownGain) countdownGain.gain.value = video.muted ? 0 : video.volume;
}

function playCountdownCue(isGo = false) {
    if (!countdownAudio || countdownAudio.state !== 'running') return;
    const now = countdownAudio.currentTime;
    // Short arcade ticks, followed by a brighter two-note start chord.
    for (const frequency of (isGo ? [880, 1320] : [660])) {
        const oscillator = countdownAudio.createOscillator();
        const envelope = countdownAudio.createGain();
        const duration = isGo ? 0.36 : 0.15;
        oscillator.type = 'triangle';
        oscillator.frequency.value = frequency;
        envelope.gain.setValueAtTime(0, now);
        envelope.gain.linearRampToValueAtTime(0.45, now + 0.008);
        envelope.gain.exponentialRampToValueAtTime(0.001, now + duration);
        oscillator.connect(envelope);
        envelope.connect(countdownGain);
        countdownVoices.add(oscillator);
        oscillator.onended = () => {
            countdownVoices.delete(oscillator);
            oscillator.disconnect();
            envelope.disconnect();
        };
        oscillator.start(now);
        oscillator.stop(now + duration + 0.02);
    }
}

function cancelCountdown() {
    countdownGeneration++;
    for (const voice of countdownVoices) voice.stop();
    countdownVoices.clear();
}

video.addEventListener('volumechange', updateCountdownVolume);
window.addEventListener('pagehide', cancelCountdown);


/* =========================================
   WAIT
========================================= */

function wait(ms) {

    return new Promise(resolve => {

        setTimeout(resolve, ms);

    });

}


/* =========================================
   FORMAT TIME
========================================= */

function formatTime(seconds) {

    if (!Number.isFinite(seconds)) {
        return "0:00";
    }


    const minutes =
        Math.floor(seconds / 60);


    const remainingSeconds =
        Math.floor(seconds % 60);


    return (
        minutes +
        ":" +
        remainingSeconds
            .toString()
            .padStart(2, "0")
    );

}


/* =========================================
   SCOREBOARD
========================================= */

function updateScoreboard(score, accuracy) {
    scoreValue.textContent = Math.round(score).toLocaleString();
}

function resetScoreboard() {

    updateScoreboard(0, 0);

}


/* =========================================
   UPDATE VIDEO PROGRESS
========================================= */

function updateProgressBar() {

    if (
        !Number.isFinite(video.duration) ||
        video.duration <= 0
    ) {
        return;
    }


    const progress =
        (
            video.currentTime /
            video.duration
        ) * 100;


    videoProgress.value =
        progress;


    videoProgress.style.setProperty(
        "--progress",
        `${progress}%`
    );


    currentTimeText.textContent =
        formatTime(video.currentTime);

}


/* =========================================
   VIDEO METADATA
========================================= */

video.addEventListener(
    "loadedmetadata",
    () => {

        durationText.textContent =
            formatTime(video.duration);


        currentTimeText.textContent =
            "0:00";


        videoProgress.value =
            0;


        videoProgress.style.setProperty(
            "--progress",
            "0%"
        );

    }
);


/* =========================================
   VIDEO TIME UPDATE
========================================= */

video.addEventListener(
    "timeupdate",
    updateProgressBar
);


/* =========================================
   SEEK VIDEO
========================================= */

videoProgress.addEventListener(
    "input",
    () => {

        if (
            !Number.isFinite(video.duration) ||
            video.duration <= 0
        ) {
            return;
        }


        const percentage =
            Number(videoProgress.value);


        const newTime =
            (
                percentage /
                100
            ) * video.duration;


        video.currentTime =
            newTime;


        videoProgress.style.setProperty(
            "--progress",
            `${percentage}%`
        );


        currentTimeText.textContent =
            formatTime(newTime);

    }
);


/* =========================================
   VOLUME UI
========================================= */

function updateVolumeUI() {

    const effectiveVolume =
        video.muted
            ? 0
            : video.volume;


    const volumePercent =
        effectiveVolume * 100;


    volumeSlider.value =
        effectiveVolume;


    volumeSlider.style.setProperty(
        "--volume-progress",
        `${volumePercent}%`
    );


    if (
        video.muted ||
        video.volume === 0
    ) {

        muteButton.textContent =
            "🔇";

    }

    else if (
        video.volume < 0.5
    ) {

        muteButton.textContent =
            "🔉";

    }

    else {

        muteButton.textContent =
            "🔊";

    }

}


/* =========================================
   VOLUME SLIDER
========================================= */

volumeSlider.addEventListener(
    "input",
    () => {

        const value =
            Math.min(
                1,
                Math.max(
                    0,
                    Number(volumeSlider.value)
                )
            );


        video.volume =
            value;


        video.muted =
            false;


        if (value > 0) {

            previousVolume =
                value;

        }


        updateVolumeUI();

    }
);


/* =========================================
   MUTE
========================================= */

muteButton.addEventListener(
    "click",
    () => {

        if (
            video.muted ||
            video.volume === 0
        ) {

            video.muted =
                false;


            video.volume =
                previousVolume > 0
                    ? previousVolume
                    : 1;

        }

        else {

            previousVolume =
                video.volume;


            video.muted =
                true;

        }


        updateVolumeUI();

    }
);


/* =========================================
   COUNTDOWN
========================================= */

async function startCountdown() {

    if (
        countdownRunning ||
        gameRunning
    ) {
        return;
    }


    countdownRunning =
        true;

    document.getElementById("playerTrackingNotice").hidden = true;
    const countdownToken = ++countdownGeneration;
    prepareCountdownAudio();
    // A gesture has no browser click permission. Audio resume may stay pending;
    // the visual countdown must proceed while prepareCountdownAudio retries it.
    if (countdownToken !== countdownGeneration) return;


    readyButton.disabled =
        true;

    readyButton.textContent = 'Starting...';


    


    startOverlay.classList.add(
        "hidden"
    );


    countdown.classList.remove(
        "hidden"
    );


    gameStatus.textContent =
        "Starting...";


    resetScoreboard();


    const numbers = [
        "3",
        "2",
        "1"
    ];


    for (
        const number of numbers
    ) {

        countdown.textContent =
            number;

        playCountdownCue();


        await wait(1000);

        if (countdownToken !== countdownGeneration) return;

    }


    countdown.textContent =
        "GO!";

    playCountdownCue(true);


    await wait(500);

    if (countdownToken !== countdownGeneration) return;


    countdown.classList.add(
        "hidden"
    );


    countdownRunning =
        false;


    await startGame();

}


/* =========================================
   START GAME
========================================= */

async function playReferenceVideo() {
    try {
        await video.play();
        return false;
    } catch (error) {
        if (error.name !== 'NotAllowedError' || video.muted) throw error;
        // Browser autoplay with sound requires a click; gesture starts can
        // still show the dancer immediately using permitted muted playback.
        video.muted = true;
        updateVolumeUI();
        updateCountdownVolume();
        await video.play();
        return true;
    }
}

async function startGame() {

    readyButton.disabled = false;
    readyButton.textContent = 'Pause';

    video.currentTime =
        0;


    gameRunning =
        true;


    isPaused =
        false;


    gameStatus.textContent =
        "Dancing";


    


    


    try {

        const mutedForAutoplay = await playReferenceVideo();
        if (mutedForAutoplay) gameStatus.textContent = 'Dancing — click the speaker to enable sound';

    }

    catch (error) {

        console.error(
            "VIDEO PLAY ERROR:",
            error
        );


        gameStatus.textContent =
            error.name === 'NotAllowedError'
                ? 'Click Ready to allow video playback'
                : 'Video could not play: ' + error.message;


        gameRunning =
            false;


        readyButton.disabled =
            false;

        readyButton.textContent = 'Ready!';


        

    }

}


/* =========================================
   PAUSE / RESUME
========================================= */

async function togglePause() {

    if (!gameRunning) {
        return;
    }


    if (video.paused) {

        try {

            await video.play();


            isPaused =
                false;


            


            


            gameStatus.textContent =
                "Dancing";

            readyButton.textContent = 'Pause';

        }

        catch (error) {

            console.error(
                "VIDEO PLAY ERROR:",
                error
            );

        }

    }

    else {

        video.pause();


        isPaused =
            true;


        


        


        gameStatus.textContent =
            "Paused";

        readyButton.textContent = 'Resume';

    }

}


/* =========================================
   RESET GAME
========================================= */

function resetGame() {

    cancelCountdown();

    video.pause();


    video.currentTime =
        0;


    gameRunning =
        false;


    isPaused =
        false;


    countdownRunning =
        false;


    countdown.classList.add(
        "hidden"
    );


    startOverlay.classList.remove(
        "hidden"
    );


    readyButton.disabled =
        false;


    readyButton.textContent =
        "Ready!";


    


    


    


    gameStatus.textContent =
        "Waiting";


    videoProgress.value =
        0;


    videoProgress.style.setProperty(
        "--progress",
        "0%"
    );


    currentTimeText.textContent =
        "0:00";


    resetScoreboard();

}


/* =========================================
   VIDEO FINISHED
========================================= */

video.addEventListener(
    "ended",
    () => {

        gameRunning =
            false;


        isPaused =
            false;


        


        


        readyButton.disabled =
            false;


        readyButton.textContent =
            "Play Again";


        gameStatus.textContent =
            "Finished";


        videoProgress.value =
            100;


        videoProgress.style.setProperty(
            "--progress",
            "100%"
        );


        currentTimeText.textContent =
            formatTime(video.duration);

    }
);


/* =========================================
   BUTTON EVENTS
========================================= */

readyButton.addEventListener(
    "click",
    () => {
        if (gameRunning) togglePause();
        else startCountdown();
    }
);





restartButton.addEventListener(
    "click",
    resetGame
);


/* =========================================
   INITIAL STATE
========================================= */

video.volume =
    1;


video.muted =
    false;


updateVolumeUI();

resetScoreboard();
