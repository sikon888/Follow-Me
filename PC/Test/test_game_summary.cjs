const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const elements = new Map();
const get = id => {
    if (!elements.has(id)) elements.set(id, {hidden: true, textContent: '',
        classList: {toggle() {}}, getContext: () => ({})});
    return elements.get(id);
};
const handlers = {};
const ctx = vm.createContext({document: {currentScript: {dataset: {}}, getElementById: get},
    video: {addEventListener(name, fn) { (handlers[name] ??= []).push(fn); }},
    readyButton: {addEventListener() {}}, restartButton: {addEventListener() {}},
    updateScoreboard() {}, resetScoreboard() {}, performance: {now: () => 0}});
const source = fs.readFileSync(path.join(__dirname, '../static/js/player.js'), 'utf8');
vm.runInContext(source.replace(/pollPiCamera\(\);\s*$/, ''), ctx);
for (const [seconds, expected] of [[0,false],[2.9,false],[3,true],[3.1,false],
    [5.9,false],[6,true],[10,true],[10.1,false],[12,true]]) {
    assert.equal(ctx.isScoreCheckpoint(seconds), expected, 'checkpoint at ' + seconds);
}
vm.runInContext('total=240; accuracySum=240; scoredSamples=4; matchedSamples=2;', ctx);
handlers.ended.forEach(fn => fn());
assert.equal(get('finalScore').textContent, '240');
assert.equal(get('finalAccuracy').textContent, '60%');
assert.equal(get('finalMatches').textContent, '2 / 4');
assert.equal(get('gameSummary').hidden, false);
vm.runInContext('clearPlayerScore()', ctx);
assert.equal(get('gameSummary').hidden, true);
handlers.ended.forEach(fn => fn());
assert.equal(get('finalAccuracy').textContent, 'No scored poses');
