// 12 second intro cinematic, drawn with the same canvas code in-game and in
// the offline MP4 renderer.  Everything is a pure function of time `t`.
(function () {
  'use strict';
  const FD = window.FD;
  const W = FD.VIEW_W;
  const H = FD.VIEW_H;

  const DURATION = 12.0;
  const LETTERBOX = 26;

  function hash(n) {
    const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return s - Math.floor(s);
  }

  function rainLayer(ctx, t, count, speed, alpha, slant) {
    ctx.save();
    ctx.strokeStyle = `rgba(168,196,230,${alpha})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let i = 0; i < count; i++) {
      const x0 = hash(i * 3.1) * (W + 60) - 30;
      const speedI = speed * (0.6 + hash(i * 7.7) * 0.8);
      const y0 = (hash(i * 5.3) * H + t * speedI * 60) % (H + 20) - 10;
      const len = 4 + hash(i * 9.1) * 8;
      ctx.moveTo(x0 + (y0 / H) * slant, y0);
      ctx.lineTo(x0 + (y0 / H) * slant + slant * 0.08, y0 + len);
    }
    ctx.stroke();
    ctx.restore();
  }

  function layer(ctx, name, camX, parallax, yOff = 0) {
    const img = FD.assets.img(`stage/layers/${name}.png`);
    if (!img) return;
    if (name === 'sky') {
      ctx.drawImage(img, 0, 0);
      return;
    }
    if (name === 'near') {
      const sx = FD.clamp(camX, 0, img.width - W);
      ctx.drawImage(img, sx, 0, W, H, 0, yOff, W, H);
      return;
    }
    const off = ((camX * parallax) % img.width + img.width) % img.width;
    for (let x = -off; x < W; x += img.width) ctx.drawImage(img, x, yOff);
  }

  function sprite(ctx, charId, anim, frame, x, y, scale = 1, opts = {}) {
    const cfg = FD.characterCfg ? FD.characterCfg(charId) : FD.cfg.animation.characters[charId];
    if (!cfg) return;
    const def = cfg.animations[anim];
    if (!def) return;
    const f = FD.clamp(frame, 0, def.frames.length - 1);
    const img = FD.assets.img(
      `characters/${charId}/frames/${anim}/${anim}_${String(f).padStart(2, '0')}.png`
    );
    if (!img) return;
    const ax = cfg.frame.anchorX;
    const ay = cfg.frame.anchorY;
    ctx.save();
    ctx.translate(x, y);
    if (opts.facing === -1) ctx.scale(-1, 1);
    if (opts.scaleX && opts.scaleX !== 1) ctx.scale(opts.scaleX, 1);
    if (opts.alpha !== undefined) ctx.globalAlpha = opts.alpha;
    if (opts.tint) {
      ctx.drawImage(img, -ax * scale, -ay * scale, img.width * scale, img.height * scale);
      ctx.globalCompositeOperation = 'source-atop';
    }
    ctx.drawImage(img, -ax * scale, -ay * scale, img.width * scale, img.height * scale);
    ctx.restore();
  }

  function flicker(t, seed, rate = 7) {
    const v = Math.sin(t * rate + seed) * Math.sin(t * rate * 2.7 + seed * 3.1);
    return v > -0.2 ? 1 : 0.25;
  }

  function letterbox(ctx, alpha = 1) {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = '#04050a';
    ctx.fillRect(0, 0, W, LETTERBOX);
    ctx.fillRect(0, H - LETTERBOX, W, LETTERBOX);
    ctx.restore();
  }

  function subtitle(ctx, text, alpha, y = H - 17, color = 'steel') {
    FD.font.draw(ctx, text, W / 2, y, { align: 'center', color, alpha, scale: 1 });
  }

  // --------------------------------------------------------------- shot 1
  function shotCity(ctx, t) {
    const local = t;
    layer(ctx, 'sky', 0, 0);
    layer(ctx, 'far', local * 70, 0.15);
    layer(ctx, 'mid', local * 70, 0.45);
    layer(ctx, 'near', 240 + local * 26, 1.0);
    // street glow
    ctx.save();
    ctx.globalAlpha = 0.5;
    ctx.fillStyle = '#101a30';
    ctx.fillRect(0, H - 40, W, 40);
    ctx.restore();
    rainLayer(ctx, t, 90, 7, 0.35, -14);
    // lightning at 1.55s and 2.3s
    const flash = t > 1.55 && t < 1.7 ? 0.5 * (1 - (t - 1.55) / 0.15) : t > 2.28 && t < 2.36 ? 0.3 : 0;
    if (flash > 0) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.fillStyle = `rgba(190,210,255,${flash})`;
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
    }
    const fadeIn = FD.clamp(local / 0.6, 0, 1);
    ctx.save();
    ctx.globalAlpha = fadeIn * 0.75;
    ctx.fillStyle = '#04050a';
    ctx.fillRect(0, 0, W, H);
    ctx.restore();
    // title type
    const typeIn = FD.clamp((local - 0.9) / 0.8, 0, 1);
    if (typeIn > 0) {
      const spacing = Math.round(FD.lerp(10, 0, FD.ease.outCubic(typeIn)));
      FD.font.draw(ctx, 'RAIN DISTRICT', W / 2, 100, {
        align: 'center', color: 'white', scale: 2, alpha: typeIn, spacing,
      });
      const rule = FD.ease.outCubic(typeIn);
      ctx.save();
      ctx.fillStyle = '#63f7ff';
      ctx.globalAlpha = typeIn;
      ctx.fillRect(W / 2 - 90 * rule, 122, 180 * rule, 1);
      ctx.restore();
      FD.font.draw(ctx, 'BLOCK 07  /  23:48', W / 2, 130, {
        align: 'center', color: 'cyanDim', alpha: typeIn * 0.9,
      });
    }
  }

  // --------------------------------------------------------------- shot 2
  function shotWalk(ctx, t) {
    // ground-level tracking shot: camera slides right with VOLT
    const local = t;
    const cam = 820 + local * 46;
    layer(ctx, 'sky', 0, 0);
    ctx.save();
    ctx.globalAlpha = 0.9;
    layer(ctx, 'mid', cam, 0.45);
    ctx.restore();
    layer(ctx, 'near', cam, 1.0);
    ctx.save();
    ctx.fillStyle = 'rgba(5,8,20,0.55)';
    ctx.fillRect(0, 0, W, H);
    ctx.restore();
    // neon sign flicker over the street
    const signOn = flicker(local, 2.1, 9);
    ctx.save();
    ctx.globalAlpha = 0.55 * signOn;
    ctx.fillStyle = '#ff5cc4';
    ctx.fillRect(332, 62, 54, 20);
    ctx.globalAlpha = 0.9 * signOn;
    ctx.fillStyle = '#1a0c16';
    FD.font.draw(ctx, 'RUSTLINE', 359, 68, { align: 'center', color: 'pink', scale: 1 });
    ctx.restore();
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.18 * signOn;
    ctx.fillStyle = '#ff5cc4';
    ctx.beginPath();
    ctx.ellipse(359, 74, 60, 22, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
    rainLayer(ctx, t, 120, 8, 0.4, -16);

    // puddle reflection band
    ctx.save();
    ctx.globalAlpha = 0.5;
    ctx.fillStyle = '#0a1424';
    ctx.fillRect(0, H - 52, W, 52);
    ctx.restore();

    // VOLT walks in from the left, lit by the neon behind him
    const walkPhase = (local * 6.5) % 6;
    const px = 168 + local * 30;
    const bob = Math.abs(Math.sin(local * 7.2)) * 1.5;
    const frame = Math.floor(walkPhase) % 6;
    // wet-ground reflection first
    ctx.save();
    ctx.globalAlpha = 0.18;
    ctx.translate(0, (H - 40) * 2);
    ctx.scale(1, -1);
    sprite(ctx, 'volt', 'walk', frame, px, H - 40 - bob, 2.1, { facing: 1 });
    ctx.restore();
    ctx.save();
    ctx.globalAlpha = 0.95;
    sprite(ctx, 'volt', 'walk', frame, px, H - 46 - bob, 2.1, { facing: 1 });
    ctx.restore();
    // rim light pass
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.12;
    sprite(ctx, 'volt', 'walk', frame, px, H - 46 - bob, 2.1, { facing: 1 });
    ctx.restore();

    const a = FD.clamp((local - 0.4) / 0.6, 0, 1) * FD.clamp((2.55 - local) / 0.5, 0, 1);
    subtitle(ctx, 'THE RUSTLINE CREW OWNS THIS BLOCK', a);
  }

  // --------------------------------------------------------------- shot 3
  function shotGauntlet(ctx, t) {
    const local = t;
    // backdrop: out-of-focus neon wall
    layer(ctx, 'sky', 0, 0);
    ctx.save();
    ctx.filter = 'none';
    ctx.globalAlpha = 0.85;
    layer(ctx, 'mid', 520, 0.45);
    ctx.restore();
    ctx.save();
    ctx.fillStyle = 'rgba(4,8,18,0.72)';
    ctx.fillRect(0, 0, W, H);
    // teal light pool behind the character
    const g = ctx.createRadialGradient(W * 0.42, H * 0.42, 20, W * 0.42, H * 0.42, 180);
    g.addColorStop(0, 'rgba(40,180,200,0.35)');
    g.addColorStop(1, 'rgba(10,20,40,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    ctx.restore();
    rainLayer(ctx, t, 60, 6, 0.22, -10);

    // hero close-up: charge pose (special frames 0-2)
    const frame = FD.clamp(Math.floor(local * 6) % 4, 0, 3);
    const zoom = 3.15 + local * 0.12;
    const ox = 232 - local * 6;
    const oy = H - 16;
    ctx.save();
    ctx.globalAlpha = 0.4;
    sprite(ctx, 'volt', 'special', frame, ox + 4, oy + 4, zoom, { facing: 1 });
    ctx.restore();
    sprite(ctx, 'volt', 'special', frame, ox, oy, zoom, { facing: 1 });
    // reflection on the ground
    ctx.save();
    ctx.globalAlpha = 0.12;
    ctx.translate(0, (H - 22) * 2);
    ctx.scale(1, -1);
    sprite(ctx, 'volt', 'special', frame, ox, oy, zoom, { facing: 1 });
    ctx.restore();

    // electric arcs
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    const arcSeed = Math.floor(local * 18);
    for (let k = 0; k < 5; k++) {
      const h1 = hash(arcSeed + k * 7);
      const h2 = hash(arcSeed * 3 + k * 11);
      const x0 = 236 + h1 * 54;
      const y0 = 40 + h2 * 64;
      ctx.strokeStyle = k % 2 ? 'rgba(150,250,255,0.9)' : 'rgba(255,255,255,0.8)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      let px = x0;
      let py = y0;
      for (let s2 = 0; s2 < 5; s2++) {
        px += (hash(arcSeed + s2 * 3.3 + k) - 0.5) * 30;
        py += (hash(arcSeed + s2 * 7.7 + k) - 0.5) * 26;
        ctx.lineTo(px, py);
      }
      ctx.stroke();
    }
    ctx.restore();

    const a = FD.clamp((local - 0.7) / 0.6, 0, 1) * FD.clamp((2.55 - local) / 0.5, 0, 1);
    FD.font.draw(ctx, 'VOLT', 352, 30, { color: 'white', scale: 3, alpha: a });
    FD.font.draw(ctx, 'ELECTRIC', 352, 60, { color: 'cyan', alpha: a });
    FD.font.draw(ctx, 'GAUNTLET', 352, 72, { color: 'cyan', alpha: a });
    subtitle(ctx, 'ONE SPARK IS ALL IT TAKES', a * 0.9);
  }

  // --------------------------------------------------------------- shot 4
  function shotStandoff(ctx, t) {
    const local = t;
    const cam = 1280 + local * 8;
    layer(ctx, 'sky', 0, 0);
    layer(ctx, 'far', cam, 0.15);
    layer(ctx, 'mid', cam, 0.45);
    layer(ctx, 'near', cam, 1.0);
    ctx.save();
    ctx.fillStyle = 'rgba(4,6,16,0.5)';
    ctx.fillRect(0, 0, W, H);
    ctx.restore();
    rainLayer(ctx, t, 140, 9, 0.42, -18);

    // three goons step out of the rain, kept as dark silhouettes
    const adv = FD.clamp(local / 2.0, 0, 1);
    const walkFrame = Math.floor(local * 7) % 6;
    const positions = [
      { x: 296 + (1 - adv) * 80, z: H - 34, s: 1.45 },
      { x: 336 + (1 - adv) * 110, z: H - 30, s: 1.58 },
      { x: 382 + (1 - adv) * 140, z: H - 36, s: 1.4 },
    ];
    positions.forEach((pos, i) => {
      ctx.save();
      ctx.globalAlpha = 0.38 + 0.22 * adv;
      ctx.filter = 'brightness(0.4) saturate(0.55)';
      sprite(ctx, 'rivet', 'walk', (walkFrame + i) % 6, pos.x, pos.z, pos.s, { facing: -1 });
      ctx.restore();
    });
    // red visor glow on the middle goon
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.fillStyle = `rgba(255,90,60,${0.75 * adv})`;
    ctx.fillRect(positions[1].x - 20, positions[1].z - 62, 3, 2);
    ctx.fillRect(positions[1].x - 14, positions[1].z - 62, 3, 2);
    ctx.restore();

    // wet street band that the title sits on
    ctx.save();
    ctx.globalAlpha = 0.85;
    ctx.fillStyle = '#04050a';
    ctx.fillRect(0, 148, W, 58);
    ctx.fillStyle = '#63f7ff';
    ctx.fillRect(0, 148, W, 1);
    ctx.fillRect(0, 205, W, 1);
    ctx.restore();

    // title slams in, left aligned so the hero can stand in front of the plate
    const slamT = FD.clamp((local - 0.9) / 0.55, 0, 1);
    if (slamT > 0) {
      const scale = FD.lerp(4.4, 2, FD.ease.outBack(slamT));
      const alpha = slamT;
      FD.font.draw(ctx, 'NEON', 176, 156, { color: 'white', scale, alpha });
      FD.font.draw(ctx, 'GAUNTLET', 176, 178, { color: 'cyan', scale, alpha });
      FD.font.draw(ctx, 'A TRIBUTE TO STREETS OF RAGE', 178, 199, {
        align: 'left', color: 'cyanDim', alpha: alpha * 0.9,
      });
    }

    // VOLT in the foreground, back to the goons, gauntlet already sparking
    const heroFrame = local < 1.0 ? 1 : local < 1.6 ? 2 : local < 2.3 ? 3 : 4;
    const heroX = 92;
    const heroY = H - 6;
    ctx.save();
    ctx.globalAlpha = 0.16;
    ctx.translate(0, heroY * 2);
    ctx.scale(1, -1);
    sprite(ctx, 'volt', 'special', heroFrame, heroX, heroY, 2.15, { facing: 1 });
    ctx.restore();
    sprite(ctx, 'volt', 'special', heroFrame, heroX, heroY, 2.15, { facing: 1 });
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.1 + 0.05 * Math.sin(local * 20);
    sprite(ctx, 'volt', 'special', heroFrame, heroX, heroY, 2.15, { facing: 1 });
    ctx.restore();
  }

  const SHOTS = [
    { start: 0.0, end: 3.0, draw: shotCity },
    { start: 3.0, end: 6.2, draw: shotWalk },
    { start: 6.2, end: 9.2, draw: shotGauntlet },
    { start: 9.2, end: 12.0, draw: shotStandoff },
  ];

  const Cinematic = {
    duration: DURATION,
    shots: SHOTS,
    draw(game, ctx, t) {
      ctx.save();
      ctx.imageSmoothingEnabled = false;
      ctx.fillStyle = '#04050a';
      ctx.fillRect(0, 0, W, H);
      const time = FD.clamp(t, 0, DURATION);
      let shot = SHOTS[SHOTS.length - 1];
      for (const s of SHOTS) {
        if (time >= s.start && time < s.end) {
          shot = s;
          break;
        }
      }
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, LETTERBOX, W, H - LETTERBOX * 2);
      ctx.clip();
      shot.draw(ctx, time - shot.start);
      ctx.restore();
      // dip-to-black transitions between shots (0.18s)
      for (const s of SHOTS) {
        const d = Math.abs(time - s.start);
        if (d < 0.18) {
          ctx.save();
          ctx.globalAlpha = 1 - d / 0.18;
          ctx.fillStyle = '#04050a';
          ctx.fillRect(0, 0, W, H);
          ctx.restore();
        }
      }
      // end fade
      if (time > DURATION - 0.5) {
        ctx.save();
        ctx.globalAlpha = (time - (DURATION - 0.5)) / 0.5;
        ctx.fillStyle = '#04050a';
        ctx.fillRect(0, 0, W, H);
        ctx.restore();
      }
      letterbox(ctx, 1);
      // skip hint only when played inside the game
      if (game && game.state === 'cinematic' && !FD.assets.filmMode) {
        FD.font.draw(ctx, 'ENTER TO SKIP', W - 8, H - 18, { align: 'right', color: 'dim', alpha: 0.7 });
      }
      ctx.restore();
    },
  };

  FD.Cinematic = Cinematic;
})();
