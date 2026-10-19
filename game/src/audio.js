// Procedural WebAudio: synthesized SFX, a looping stage track and rain bed.
// Nothing is sampled from a commercial game; all buffers are generated here.
(function () {
  'use strict';
  const FD = window.FD;

  let ctx = null;
  let master = null;
  let musicGain = null;
  let sfxGain = null;
  let rainGain = null;
  let muted = false;
  let started = false;
  let musicSource = null;

  function makeNoiseBuffer(seconds, secondsSeed = 1) {
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    let last = 0;
    for (let i = 0; i < len; i++) {
      const white = Math.random() * 2 - 1;
      last = 0.96 * last + 0.04 * white;
      d[i] = white * 0.7 + last * 0.6;
    }
    return buf;
  }

  function synthPunch(heavy) {
    const dur = heavy ? 0.24 : 0.15;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * dur), ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) {
      const t = i / ctx.sampleRate;
      const env = Math.exp(-t * (heavy ? 26 : 42));
      const thump = Math.sin(2 * Math.PI * (heavy ? 78 : 122) * t) * env;
      const crack = (Math.random() * 2 - 1) * env * (heavy ? 0.5 : 0.32);
      d[i] = (thump * 0.8 + crack) * 0.9;
    }
    return buf;
  }

  function synthZap() {
    const dur = 0.55;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * dur), ctx.sampleRate);
    const d = buf.getChannelData(0);
    let phase = 0;
    for (let i = 0; i < d.length; i++) {
      const t = i / ctx.sampleRate;
      const env = Math.exp(-t * 6) * (0.6 + 0.4 * Math.sin(t * 90));
      const f = 1400 - 1100 * Math.min(1, t / dur);
      phase += (2 * Math.PI * f) / ctx.sampleRate;
      const tone = Math.sin(phase) * 0.45 + (Math.random() * 2 - 1) * 0.25;
      d[i] = tone * env * 0.8;
    }
    return buf;
  }

  function synthHurt() {
    const dur = 0.22;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * dur), ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) {
      const t = i / ctx.sampleRate;
      const env = Math.exp(-t * 18);
      const f = 380 - 160 * (t / dur);
      d[i] = (Math.sin(2 * Math.PI * f * t) * 0.5 + (Math.random() * 2 - 1) * 0.2) * env;
    }
    return buf;
  }

  function synthPickup() {
    const dur = 0.3;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * dur), ctx.sampleRate);
    const d = buf.getChannelData(0);
    const notes = [880, 1320, 1760];
    for (let i = 0; i < d.length; i++) {
      const t = i / ctx.sampleRate;
      const step = Math.min(2, Math.floor(t / 0.08));
      const env = Math.exp(-((t - step * 0.08) * 22));
      d[i] = Math.sin(2 * Math.PI * notes[step] * t) * env * 0.35;
    }
    return buf;
  }

  function synthBreak() {
    const dur = 0.4;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * dur), ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) {
      const t = i / ctx.sampleRate;
      const env = Math.exp(-t * 9);
      d[i] = (Math.random() * 2 - 1) * env * (0.5 + 0.5 * Math.sin(t * 60));
    }
    return buf;
  }

  function synthSelect() {
    const dur = 0.12;
    const buf = ctx.createBuffer(1, Math.floor(ctx.sampleRate * dur), ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) {
      const t = i / ctx.sampleRate;
      d[i] = Math.sin(2 * Math.PI * 660 * t) * Math.exp(-t * 20) * 0.3;
    }
    return buf;
  }

  const buffers = {};

  function buildStageMusic() {
    // 8 bars of 16th notes at 128 BPM, 4/4. Original composition.
    const bpm = 128;
    const beat = 60 / bpm;
    const bars = 8;
    const total = beat * 4 * bars;
    const sr = ctx.sampleRate;
    const buf = ctx.createBuffer(2, Math.floor(sr * total), sr);
    const L = buf.getChannelData(0);
    const R = buf.getChannelData(1);
    const bassNotes = [55, 55, 65.4, 49, 55, 55, 73.4, 49]; // A1 A1 C2 G1 ... a minor-ish loop
    const leadNotes = [220, 261.6, 329.6, 392, 329.6, 261.6, 293.7, 246.9];
    const steps = 16 * 4;
    const stepDur = total / (steps * bars / 8) / 4;
    const sixteenth = beat / 4;
    for (let bar = 0; bar < bars; bar++) {
      for (let s = 0; s < 16; s++) {
        const t0 = bar * beat * 4 + s * sixteenth;
        const idx = Math.floor((t0 / total) * steps) % steps;
        // kick on 1 and 3
        if (s % 8 === 0 || s === 10) {
          addKick(L, R, t0, sr);
        }
        // snare on 2 and 4
        if (s === 4 || s === 12) addSnare(L, R, t0, sr);
        // hats on every off 8th
        if (s % 2 === 1) addHat(L, R, t0, sr);
        // bass on 8ths
        if (s % 2 === 0) {
          const n = bassNotes[(bar + Math.floor(s / 8)) % bassNotes.length];
          addBass(L, R, t0, n, sixteenth * 1.6, sr);
        }
        // arpeggio lead on a sparse pattern
        if ([0, 3, 6, 10, 13].includes(s)) {
          const n = leadNotes[(bar * 2 + s) % leadNotes.length] * (bar >= 4 ? 1.5 : 1);
          addLead(L, R, t0, n, sixteenth * 1.2, sr);
        }
      }
    }
    // gentle bus compression via soft clip
    for (let i = 0; i < L.length; i++) {
      L[i] = Math.tanh(L[i] * 1.2) * 0.7;
      R[i] = Math.tanh(R[i] * 1.2) * 0.7;
    }
    return buf;
  }

  function addKick(L, R, t0, sr) {
    const start = Math.floor(t0 * sr);
    const n = Math.floor(0.22 * sr);
    for (let i = 0; i < n && start + i < L.length; i++) {
      const t = i / sr;
      const f = 120 * Math.exp(-t * 30) + 42;
      const v = Math.sin(2 * Math.PI * f * t) * Math.exp(-t * 14) * 0.85;
      L[start + i] += v;
      R[start + i] += v;
    }
  }
  function addSnare(L, R, t0, sr) {
    const start = Math.floor(t0 * sr);
    const n = Math.floor(0.18 * sr);
    for (let i = 0; i < n && start + i < L.length; i++) {
      const t = i / sr;
      const env = Math.exp(-t * 24);
      const noise = Math.random() * 2 - 1;
      const body = Math.sin(2 * Math.PI * 190 * t) * 0.4;
      L[start + i] += (noise * 0.5 + body) * env * 0.45;
      R[start + i] += (noise * 0.5 + body) * env * 0.45;
    }
  }
  function addHat(L, R, t0, sr) {
    const start = Math.floor(t0 * sr);
    const n = Math.floor(0.05 * sr);
    for (let i = 0; i < n && start + i < L.length; i++) {
      const t = i / sr;
      const v = (Math.random() * 2 - 1) * Math.exp(-t * 60) * 0.12;
      L[start + i] += v * 0.8;
      R[start + i] += v;
    }
  }
  function addBass(L, R, t0, freq, dur, sr) {
    const start = Math.floor(t0 * sr);
    const n = Math.floor(dur * sr);
    for (let i = 0; i < n && start + i < L.length; i++) {
      const t = i / sr;
      const env = Math.min(1, t * 80) * Math.exp(-t * 2.2);
      const v = (Math.sin(2 * Math.PI * freq * t) + 0.4 * Math.sin(2 * Math.PI * freq * 2 * t)) * env * 0.32;
      L[start + i] += v;
      R[start + i] += v;
    }
  }
  function addLead(L, R, t0, freq, dur, sr) {
    const start = Math.floor(t0 * sr);
    const n = Math.floor(dur * sr);
    for (let i = 0; i < n && start + i < L.length; i++) {
      const t = i / sr;
      const env = Math.min(1, t * 120) * Math.exp(-t * 7);
      const v = (Math.sin(2 * Math.PI * freq * t) * 0.18 + Math.sin(2 * Math.PI * freq * 1.005 * t) * 0.1) * env;
      L[start + i] += v * 0.7;
      R[start + i] += v;
    }
  }

  function playBuffer(buf, gainNode, when = 0, loop = false) {
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = loop;
    src.connect(gainNode);
    src.start(ctx.currentTime + when);
    return src;
  }

  const audio = {
    get available() { return !!ctx; },
    get muted() { return muted; },

    init() {
      if (ctx) return;
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = 0.8;
      const comp = ctx.createDynamicsCompressor();
      comp.threshold.value = -18;
      comp.knee.value = 12;
      comp.ratio.value = 5;
      master.connect(comp);
      comp.connect(ctx.destination);
      musicGain = ctx.createGain();
      musicGain.gain.value = 0.34;
      musicGain.connect(master);
      sfxGain = ctx.createGain();
      sfxGain.gain.value = 0.65;
      sfxGain.connect(master);
      rainGain = ctx.createGain();
      rainGain.gain.value = 0.0;
      rainGain.connect(master);
      buffers.punch = synthPunch(false);
      buffers.punchHeavy = synthPunch(true);
      buffers.zap = synthZap();
      buffers.hurt = synthHurt();
      buffers.pickup = synthPickup();
      buffers.break = synthBreak();
      buffers.select = synthSelect();
      buffers.music = buildStageMusic();
      buffers.rain = makeNoiseBuffer(4);
    },

    async unlock() {
      if (!ctx) this.init();
      if (!ctx) return;
      if (ctx.state === 'suspended') await ctx.resume();
      if (!started) {
        started = true;
        musicSource = playBuffer(buffers.music, musicGain, 0, true);
        const rain = ctx.createBufferSource();
        rain.buffer = buffers.rain;
        rain.loop = true;
        const lp = ctx.createBiquadFilter();
        lp.type = 'lowpass';
        lp.frequency.value = 1600;
        rain.connect(lp);
        lp.connect(rainGain);
        rain.start();
        rainGain.gain.setTargetAtTime(0.09, ctx.currentTime, 1.2);
      }
    },

    setMuted(m) {
      muted = m;
      if (!ctx) return;
      master.gain.setTargetAtTime(m ? 0 : 0.8, ctx.currentTime, 0.05);
      try { localStorage.setItem('fd-muted', m ? '1' : '0'); } catch (e) { /* ignore */ }
    },

    restoreMuted() {
      try { muted = localStorage.getItem('fd-muted') === '1'; } catch (e) { muted = false; }
      if (ctx) master.gain.value = muted ? 0 : 0.8;
    },

    duckMusic(onStage) {
      if (!ctx) return;
      musicGain.gain.setTargetAtTime(onStage ? 0.34 : 0.12, ctx.currentTime, 0.4);
      rainGain.gain.setTargetAtTime(onStage ? 0.09 : 0.02, ctx.currentTime, 0.6);
    },

    play(name, opts = {}) {
      if (!ctx || muted) return;
      const map = {
        punch: ['punch', 0.9], punch_heavy: ['punchHeavy', 1.0], kick_heavy: ['punchHeavy', 1.1],
        zap: ['zap', 1.0], hurt: ['hurt', 0.9], pickup: ['pickup', 0.8],
        break: ['break', 0.8], select: ['select', 0.7], land: ['punch', 0.35],
      };
      const entry = map[name];
      if (!entry) return;
      const [bufName, vol] = entry;
      const g = ctx.createGain();
      g.gain.value = vol * (opts.volume === undefined ? 1 : opts.volume);
      g.connect(sfxGain);
      const src = ctx.createBufferSource();
      src.buffer = buffers[bufName];
      if (opts.rate) src.playbackRate.value = opts.rate;
      src.connect(g);
      src.start();
    },

    stopMusic() {
      if (musicSource) {
        try { musicSource.stop(); } catch (e) { /* already stopped */ }
        musicSource = null;
      }
    },
  };

  FD.audio = audio;
})();
