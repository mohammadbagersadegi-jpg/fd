// Asset loading.  In normal HTTP mode images come from game/assets/*.
// Captured film pages inject window.FD_FILM = { data, assets: {path: dataURI},
// font, cinematic } so the very same build renders inside a headless browser
// without a network server.
(function () {
  'use strict';
  const FD = window.FD;

  const CHAR_IDS = ['volt', 'rivet'];

  FD.assets = {
    images: Object.create(null),
    ready: false,
    failures: [],

    isFilm() {
      return !!window.FD_FILM;
    },

    data() {
      return window.FD_FILM ? window.FD_FILM.data : window.FD_DATA;
    },

    font() {
      return window.FD_FILM && window.FD_FILM.font ? window.FD_FILM.font : window.FD_FONT;
    },

    cinematic() {
      return window.FD_FILM && window.FD_FILM.cinematic ? window.FD_FILM.cinematic : window.FD_CINEMATIC;
    },

    // Build the full list of image paths from the config (no runtime JSON fetch).
    listImages(data) {
      const paths = new Set();
      for (const charId of CHAR_IDS) {
        const cfg = data.animation.characters[charId === 'rivet_elite' ? 'rivet' : charId];
        if (!cfg) continue;
        for (const [anim, spec] of Object.entries(cfg.animations)) {
          spec.frames.forEach((f, i) => {
            paths.add(`characters/${charId}/frames/${anim}/${anim}_${String(i).padStart(2, '0')}.png`);
          });
        }
      }
      const stage = data.stage;
      for (const layer of ['sky', 'far', 'mid', 'near', 'fg']) paths.add(`stage/layers/${layer}.png`);
      for (const prop of ['crate', 'barrel', 'trash']) {
        paths.add(`stage/props/${prop}_0.png`);
        paths.add(`stage/props/${prop}_1.png`);
      }
      paths.add('stage/props/pickup_health.png');
      paths.add('stage/props/pickup_score.png');
      paths.add('stage/props/light_pool.png');
      paths.add('ui/logo.png');
      paths.add('ui/hud_panel.png');
      paths.add('ui/portrait_frame.png');
      paths.add('ui/scanline.png');
      return Array.from(paths);
    },

    srcFor(relPath) {
      if (window.FD_FILM && window.FD_FILM.assets && window.FD_FILM.assets[relPath]) {
        return window.FD_FILM.assets[relPath];
      }
      return `assets/${relPath}`;
    },

    loadImage(relPath) {
      return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => resolve({ path: relPath, img });
        img.onerror = () => resolve({ path: relPath, img: null });
        img.src = this.srcFor(relPath);
      });
    },

    async load(progressCb) {
      const data = this.data();
      const font = this.font();
      if (!data) throw new Error('No config data: include src/generated/data.js');
      if (!font) throw new Error('No font data: include src/generated/font.js');
      this.dataRef = data;
      this.fontRef = font;
      const paths = this.listImages(data);
      let loaded = 0;
      const results = await Promise.all(
        paths.map((p) =>
          this.loadImage(p).then((r) => {
            loaded += 1;
            if (progressCb) progressCb(loaded, paths.length);
            return r;
          })
        )
      );
      for (const r of results) {
        if (r.img) this.images[r.path] = r.img;
        else this.failures.push(r.path);
      }
      this.ready = true;
      if (this.failures.length) {
        console.warn('[assets] missing images:', this.failures);
      }
      return this;
    },

    img(relPath) {
      return this.images[relPath] || null;
    },
  };

  // Convenience accessors used across modules.
  FD.characterCfg = function (charId) {
    const chars = FD.assets.dataRef.animation.characters;
    return chars[charId] || chars[String(charId).replace('_elite', '')];
  };

  FD.cfg = {
    get movement() { return FD.assets.dataRef.movement; },
    get collision() { return FD.assets.dataRef.collision; },
    get combat() { return FD.assets.dataRef.combat; },
    get animation() { return FD.assets.dataRef.animation; },
    get stage() { return FD.assets.dataRef.stage; },
    get presentation() { return FD.assets.dataRef.presentation; },
  };
})();
