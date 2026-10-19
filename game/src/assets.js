// Asset loading.  In normal HTTP mode images come from game/assets/*.
// An embed (the single-file build in dist/, or a captured film page) injects
// window.FD_EMBED = { assets: {path: dataURI}, data?, font?, cinematic? } so the
// same modules run from a file:// URL with no server and no network.
(function () {
  'use strict';
  const FD = window.FD;

  const CHAR_IDS = ['volt', 'rivet'];

  FD.assets = {
    images: Object.create(null),
    ready: false,
    failures: [],

    embed() {
      return window.FD_EMBED || window.FD_FILM || null;
    },

    isFilm() {
      return !!window.FD_FILM;
    },

    data() {
      const e = this.embed();
      return e && e.data ? e.data : window.FD_DATA;
    },

    font() {
      const e = this.embed();
      return e && e.font ? e.font : window.FD_FONT;
    },

    cinematic() {
      const e = this.embed();
      return e && e.cinematic ? e.cinematic : window.FD_CINEMATIC;
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
      const e = this.embed();
      if (e && e.assets && e.assets[relPath]) return e.assets[relPath];
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

  // The bundle is already on the page (data.js or an embed), so expose it
  // synchronously.  FD.boot() creates the Game before assets.load() resolves
  // and createGame() reads FD.cfg.presentation.
  FD.assets.dataRef = FD.assets.data() || null;
  FD.assets.fontRef = FD.assets.font() || null;

  // Convenience accessors used across modules.
  FD.characterCfg = function (charId) {
    const chars = FD.assets.dataRef.animation.characters;
    return chars[charId] || chars[String(charId).replace('_elite', '')];
  };

  const section = (key) => (FD.assets.dataRef ? FD.assets.dataRef[key] : null);
  FD.cfg = {
    get movement() { return section('movement'); },
    get collision() { return section('collision'); },
    get combat() { return section('combat'); },
    get animation() { return section('animation'); },
    get stage() {
      const d = FD.assets.dataRef;
      if (!d) return null;
      if (d.currentStage) return d.currentStage;
      const list = FD.stageList();
      return list[0] || d.stage || null;
    },
    get presentation() { return section('presentation'); },
  };

  // ---- eight-stage campaign -------------------------------------------------
  // config/stages.json holds the whole campaign.  The runtime keeps the active
  // stage in `currentStage` so every module can keep reading FD.cfg.stage.
  FD.stageList = function () {
    const data = FD.assets.dataRef;
    const raw = data && data.stages;
    if (!raw) return data && data.stage ? [data.stage] : [];
    return Array.isArray(raw) ? raw : raw.stages || [];
  };

  FD.setStage = function (index) {
    const list = FD.stageList();
    if (!list.length) return null;
    const i = Math.max(0, Math.min(list.length - 1, index | 0));
    const copy = JSON.parse(JSON.stringify(list[i]));
    FD.assets.dataRef.currentStage = copy;
    return copy;
  };
})();
