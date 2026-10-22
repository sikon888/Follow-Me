const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/player.js'), 'utf8');
new vm.Script(source); // Check the complete browser script's syntax.
function setup() {
    const ctx = vm.createContext({gameRunning: false, countdownRunning: false,
        piPreview: {height: 360}, playerPoseStatus: {}, starts: 0,
        clearPlayerScore() {}, startCountdown() { ctx.starts++; }});
    vm.runInContext(`let handRaisedSince=null, lastGestureSample=null,
        gestureSamples=0, gestureLatched=false;\n` + source.slice(
        source.indexOf('function resetStartGesture()'), source.indexOf('function clearPlayerScore()')), ctx);
    return ctx;
}
function pose(shoulder, wrist) {
    const p = Array.from({length: 17}, () => [0, 0, 0]);
    p[0] = [240, 100, .4]; p[shoulder] = [200, 180, .4];
    p[wrist] = [200, 50, .4];
    return p;
}
for (const [shoulder, wrist] of [[5,9], [6,10]]) {
    const c = setup(), p = pose(shoulder, wrist);
    p[shoulder][2] = 0; // A raised wrist needs no visible shoulder.
    c.updateStartGesture(p, 0);
    assert.match(c.playerPoseStatus.textContent, /2\.0 s more/);
    c.updateStartGesture(p, 600);
    assert.match(c.playerPoseStatus.textContent, /1\.4 s more/);
    c.updateStartGesture(p, 1200);
    assert.equal(c.starts, 0, 'One second must not start the game');
    c.updateStartGesture(p, 2000); c.updateStartGesture(p, 3000);
    c.updateStartGesture(p, 3600);
    assert.equal(c.starts, 1, 'Either arm works; a held hand triggers once');
}
{
    const c = setup(), p = pose(5,9);
    c.updateStartGesture(p, 0); c.updateStartGesture(p, 1500);
    assert.equal(c.starts, 0);
    c.updateStartGesture(p, 3000);
    assert.equal(c.starts, 1, 'Slow inference can still trigger');
}
for (const kind of ['lowered', 'missing', 'nan', 'gap']) {
    const c = setup(), p = pose(5,9);
    if (kind === 'lowered') p[9][1] = 130;
    if (kind === 'missing') p[9][2] = .1;
    if (kind === 'nan') p[9][0] = NaN;
    c.updateStartGesture(p, 0); c.updateStartGesture(p, kind === 'gap' ? 4000 : 1500);
    assert.equal(c.starts, 0, kind + ' must not start');
}
console.log('Hand-raise regression checks passed');

// Browser autoplay restrictions must never block the visual countdown.
const gameSource = fs.readFileSync(path.join(__dirname, '../static/js/game.js'), 'utf8');
new vm.Script(gameSource);
const classes = () => ({add() {}, remove() {}});
const audioCtx = vm.createContext({
    countdownRunning: false, gameRunning: false, countdownGeneration: 0,
    countdownAudio: {state: 'suspended', resume: () => new Promise(() => {})},
    prepareCountdownAudio() {}, readyButton: {}, gameStatus: {},
    startOverlay: {classList: classes()}, countdown: {classList: classes()},
    resetScoreboard() {}, document: {getElementById: () => ({hidden: false})},
});
vm.runInContext(gameSource.slice(gameSource.indexOf('async function startCountdown()'),
    gameSource.indexOf('    const numbers =', gameSource.indexOf('async function startCountdown()'))) + '}', audioCtx);
audioCtx.startCountdown();
assert.equal(audioCtx.readyButton.textContent, 'Starting...',
    'Visual countdown starts even if browser audio resume never resolves');
console.log('Gesture countdown works with blocked audio');
