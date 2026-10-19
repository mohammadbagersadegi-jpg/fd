// 5x7 bitmap font renderer with cached colour atlases.
(function () {
  'use strict';
  const FD = window.FD;

  const PALETTE = {
    white: '#f2f0e8',
    dim: '#8d93a8',
    cyan: '#63f7ff',
    cyanDim: '#2aa9be',
    pink: '#ff5cc4',
    amber: '#ffbe5c',
    red: '#ff5a52',
    green: '#78ffa8',
    ink: '#0a0d18',
    gold: '#ffd166',
    steel: '#b8c4d0',
  };

  const cache = Object.create(null);

  function buildAtlas(color) {
    const font = FD.assets.fontRef;
    const chars = Object.keys(font.glyphs);
    const cellW = font.width + 1;
    const cellH = font.height + 1;
    const cols = 16;
    const rows = Math.ceil(chars.length / cols);
    const cv = document.createElement('canvas');
    cv.width = cols * cellW;
    cv.height = rows * cellH;
    const ctx = cv.getContext('2d');
    ctx.fillStyle = color;
    chars.forEach((ch, i) => {
      const rowsG = font.glyphs[ch];
      const ox = (i % cols) * cellW;
      const oy = Math.floor(i / cols) * cellH;
      for (let y = 0; y < rowsG.length; y++) {
        const row = rowsG[y];
        for (let x = 0; x < row.length; x++) {
          if (row[x] === '#') ctx.fillRect(ox + x, oy + y, 1, 1);
        }
      }
    });
    return { canvas: cv, index: Object.fromEntries(chars.map((c, i) => [c, i])), cols, cellW, cellH };
  }

  const font = {
    PALETTE,
    atlas(color) {
      const key = color in PALETTE ? color : 'custom';
      if (!cache[key]) cache[key] = buildAtlas(key === 'custom' ? color : PALETTE[key]);
      return cache[key];
    },
    width(text, scale = 1, spacing = 0) {
      const f = FD.assets.fontRef;
      return text.length * (f.advance + spacing) * scale - spacing * scale;
    },
    // opts: scale, color, shadow (colour or null), align ('left'|'center'|'right'),
    //       alpha, spacing
    draw(ctx, text, x, y, opts = {}) {
      const color = opts.color || 'white';
      const scale = opts.scale || 1;
      const shadow = opts.shadow === undefined ? 'ink' : opts.shadow;
      const spacing = opts.spacing || 0;
      const alpha = opts.alpha === undefined ? 1 : opts.alpha;
      const f = FD.assets.fontRef;
      const adv = (f.advance + spacing) * scale;
      let px = x;
      const upper = String(text).toUpperCase();
      const w = upper.length * adv - spacing * scale;
      if (opts.align === 'center') px = Math.round(x - w / 2);
      else if (opts.align === 'right') px = Math.round(x - w);
      px = Math.round(px);
      const py = Math.round(y);
      ctx.save();
      ctx.globalAlpha = alpha;
      if (shadow) {
        this._blit(ctx, upper, px + scale, py + scale, this.atlas(shadow), scale, adv, spacing);
      }
      this._blit(ctx, upper, px, py, this.atlas(color), scale, adv, spacing);
      ctx.restore();
      return w;
    },
    _blit(ctx, text, x, y, atlas, scale, adv, spacing) {
      for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (ch === ' ') continue;
        const idx = atlas.index[ch];
        if (idx === undefined) continue;
        const sx = (idx % atlas.cols) * atlas.cellW;
        const sy = Math.floor(idx / atlas.cols) * atlas.cellH;
        ctx.drawImage(atlas.canvas, sx, sy, atlas.cellW, atlas.cellH,
          Math.round(x + i * adv), Math.round(y), atlas.cellW * scale, atlas.cellH * scale);
      }
    },
  };

  FD.font = font;
})();
