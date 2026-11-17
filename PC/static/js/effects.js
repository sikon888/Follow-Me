// Shared decorations and a short, quiet UI sound, including dynamic buttons.
(() => {
    let audio;
    document.addEventListener('click', async event => {
        const button = event.target.closest('button, a[href], input[type="submit"], [role="button"]');
        if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true') return;
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            audio ??= new AudioContext();
            if (audio.state === 'suspended') await audio.resume();
            const oscillator = audio.createOscillator();
            const gain = audio.createGain();
            const now = audio.currentTime;
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(880, now);
            oscillator.frequency.exponentialRampToValueAtTime(1320, now + 0.045);
            gain.gain.setValueAtTime(0, now);
            gain.gain.linearRampToValueAtTime(0.045, now + 0.005);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
            oscillator.connect(gain);
            gain.connect(audio.destination);
            oscillator.start(now);
            oscillator.stop(now + 0.09);
            oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
        } catch {
            // Audio availability must never prevent a button action.
        }
    }, true);

    const glitter = document.createElement('div');
    glitter.className = 'page-glitter';
    glitter.setAttribute('aria-hidden', 'true');
    for (let i = 0; i < 28; i++) {
        const sparkle = document.createElement('span');
        sparkle.className = 'page-sparkle';
        sparkle.style.left = `${Math.random() * 100}%`;
        sparkle.style.top = `${Math.random() * 100}%`;
        sparkle.style.setProperty('--sparkle-size', `${3 + Math.random() * 5}px`);
        sparkle.style.animationDelay = `${-Math.random() * 6}s`;
        sparkle.style.animationDuration = `${4 + Math.random() * 4}s`;
        glitter.append(sparkle);
    }
    document.body.append(glitter);

    const stage = document.createElement('div');
    stage.className = 'rhythm-stage';
    stage.setAttribute('aria-hidden', 'true');
    const grid = document.createElement('div');
    grid.className = 'rhythm-grid';
    const equalizer = document.createElement('div');
    equalizer.className = 'rhythm-equalizer';
    for (let i = 0; i < 32; i++) {
        const bar = document.createElement('i');
        bar.style.setProperty('--bar-height', `${20 + (Math.sin(i * 1.7) + 1) * 35}px`);
        bar.style.animationDelay = `${-(i % 7) * 0.19}s`;
        equalizer.append(bar);
    }
    stage.append(grid, equalizer);
    document.body.prepend(stage);

    document.addEventListener('click', event => {
        const button = event.target.closest('button, a[href], input[type="submit"], [role="button"]');
        if (button && (button.disabled || button.getAttribute('aria-disabled') === 'true')) return;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
        if (!event.detail && !button) return;
        const bounds = button?.getBoundingClientRect();
        const x = event.detail ? event.clientX : bounds.left + bounds.width / 2;
        const y = event.detail ? event.clientY : bounds.top + bounds.height / 2;
        const burst = document.createElement('div');
        burst.className = 'rhythm-burst';
        burst.style.left = `${x}px`;
        burst.style.top = `${y}px`;
        const ring = document.createElement('span');
        ring.className = 'rhythm-hit';
        burst.append(ring);
        for (let i = 0; i < 10; i++) {
            const spark = document.createElement('span');
            spark.className = 'rhythm-click-spark';
            const angle = i * Math.PI * 2 / 10;
            const distance = 30 + Math.random() * 25;
            spark.style.setProperty('--spark-x', `${Math.cos(angle) * distance}px`);
            spark.style.setProperty('--spark-y', `${Math.sin(angle) * distance}px`);
            burst.append(spark);
        }
        document.body.append(burst);
        setTimeout(() => burst.remove(), 650);
    }, true);
})();
