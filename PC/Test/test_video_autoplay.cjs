const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/js/game.js'), 'utf8');
module.exports = (async () => {
    for (const kind of ['allowed', 'blocked', 'codec']) {
        let calls = 0;
        const ctx = vm.createContext({video: {muted: false, async play() {
            calls++;
            if (kind === 'blocked' && calls === 1) throw {name: 'NotAllowedError'};
            if (kind === 'codec') throw {name: 'NotSupportedError'};
        }}, updateVolumeUI() {}, updateCountdownVolume() {}});
        vm.runInContext(source.slice(source.indexOf('async function playReferenceVideo()'),
            source.indexOf('async function startGame()')), ctx);
        if (kind === 'codec') {
            await assert.rejects(ctx.playReferenceVideo(), e => e.name === 'NotSupportedError');
            assert.equal(calls, 1);
        } else {
            assert.equal(await ctx.playReferenceVideo(), kind === 'blocked');
            assert.equal(ctx.video.muted, kind === 'blocked');
            assert.equal(calls, kind === 'blocked' ? 2 : 1);
        }
    }
})();
