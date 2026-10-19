// NEON GAUNTLET - core helpers
// Virtual resolution 480x270 @ 60 ticks per second.
(function () {
  'use strict';
  const FD = (window.FD = window.FD || {});

  FD.VERSION = '1.0.0';
  FD.VIEW_W = 480;
  FD.VIEW_H = 270;
  FD.TICK_HZ = 60;

  FD.clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
  FD.lerp = (a, b, t) => a + (b - a) * t;
  FD.sign = (v) => (v > 0 ? 1 : v < 0 ? -1 : 0);
  FD.approach = (v, target, step) => {
    if (v < target) return Math.min(target, v + step);
    if (v > target) return Math.max(target, v - step);
    return v;
  };
  FD.rectsOverlap = (a, b) =>
    a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;

  // Deterministic PRNG (mulberry32) so tests and recordings replay exactly.
  FD.makeRng = function (seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  FD.ease = {
    outQuad: (t) => 1 - (1 - t) * (1 - t),
    inQuad: (t) => t * t,
    outCubic: (t) => 1 - Math.pow(1 - t, 3),
    inOutSine: (t) => -(Math.cos(Math.PI * t) - 1) / 2,
    outBack: (t) => 1 + 2.2 * Math.pow(t - 1, 3) + 1.2 * Math.pow(t - 1, 2),
  };

  FD.pad = (n, len) => String(Math.max(0, Math.floor(n))).padStart(len, '0');
  FD.fmtTime = (ticks) => {
    const total = Math.max(0, Math.floor(ticks / 60));
    return `${FD.pad(Math.floor(total / 60), 1)}:${FD.pad(total % 60, 2)}`;
  };

  // Registry of sound events fired during a tick; the audio module drains it.
  FD.sfxQueue = [];
  FD.sfx = (name, opts) => FD.sfxQueue.push(Object.assign({ name }, opts || {}));
})();
