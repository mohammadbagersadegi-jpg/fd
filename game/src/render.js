// Canvas renderer: parallax city, rain, depth-sorted actors, effects and HUD.
(function () {
  'use strict';
  const FD = window.FD;
  const R = {};

  const LAYERS = [
    { name: 'sky', parallax: 0, tile: false },
    { name: 'far', parallax: 0.15, tile: true },
    { name: 'mid', parallax: 0.45, tile: true },
    { name: 'near', parallax: 1.0, tile: false },
    { name: 'fg', parallax: 1.18, tile: true },
  ];

  const tintCache = new Map();

  function tinted(img, color) {
    const key = img.src + '|' + color;
    if (tintCache.has(key)) return tintCache.get(key);
    const cv = document.createElement('canvas');
    cv.width = img.width;
    cv.height = img.height;
    const c = cv.getContext('2d');
    c.drawImage(img, 0, 0);
    c.globalCompositeOperation = 'source-atop';
    c.fillStyle = color;
    c.fillRect(0, 0, cv.width, cv.height);
    tintCache.set(key, cv);
    const white = document.createElement('canvas');
    white.width = img.width;
    white.height = img.height;
    const wc = white.getContext('2d');
    wc.drawImage(img, 0, 0);
    wc.globalCompositeOperation = 'source-in';
    wc.fillStyle = color;
    wc.fillRect(0, 0, white.width, white.height);
    tintCache.set(key + '|silhouette', white);
    return cv;
  }

  function silhouette(img, color) {
    tinted(img, color);
    return tintCache.get(img.src + '|' + color + '|silhouette');
  }

  R.init = function (game) {
    const data = FD.assets.data();
    game.film = data.stage;
    game.rain = [];
    const cfg = FD.cfg.presentation.weather;
    for (let i = 0; i < cfg.rainDrops; i++) {
      game.rain.push({
        x: Math.random() * (FD.VIEW_W + 80) - 40,
        y: Math.random() * FD.VIEW_H,
        len: 3 + Math.random() * 7,
        speed: cfg.rainSpeed * (0.7 + Math.random() * 0.7),
        splash: 0,
      });
    }
    game.splashes = [];
    game.lightning = { next: cfg.lightningMinTicks + Math.random() * (cfg.lightningMaxTicks - cfg.lightningMinTicks), flash: 0 };
    game.scanPattern = null;
    const scan = FD.assets.img('ui/scanline.png');
    if (scan) game.scanPattern = game.ctx.createPattern(scan, 'repeat');
    game.vignette = null;
  };

  R.updateWeather = function (game) {
    const w = FD.cfg.presentation.weather;
    const drops = game.rain;
    for (const d of drops) {
      d.y += d.speed;
      d.x += d.speed * w.rainAngle;
      if (d.y > FD.VIEW_H + 8) {
        d.y = -8 - Math.random() * 40;
        d.x = Math.random() * (FD.VIEW_W + 80) - 40;
        if (Math.random() < w.splashChance) {
          game.splashes.push({ x: d.x, y: FD.VIEW_H - 6 - Math.random() * 16, t: 0, life: 8 });
        }
      }
      if (d.x < -45) d.x += FD.VIEW_W + 90;
      if (d.x > FD.VIEW_W + 45) d.x -= FD.VIEW_W + 90;
    }
    for (let i = game.splashes.length - 1; i >= 0; i--) {
      const s = game.splashes[i];
      s.t += 1;
      if (s.t > s.life) game.splashes.splice(i, 1);
    }
    const lg = game.lightning;
    lg.next -= 1;
    if (lg.next <= 0) {
      lg.flash = 12;
      lg.next = w.lightningMinTicks + Math.random() * (w.lightningMaxTicks - w.lightningMinTicks);
      FD.sfx('break', { volume: 0.18, rate: 0.5 });
    }
    if (lg.flash > 0) lg.flash -= 1;
  };

  // ------------------------------------------------------------------ world
  function drawBackdrop(game, ctx) {
    const cam = game.camera.x;
    for (const layer of LAYERS) {
      const img = FD.assets.img(`stage/layers/${layer.name}.png`);
      if (!img) continue;
      if (layer.name === 'sky') {
        ctx.drawImage(img, 0, 0);
        continue;
      }
      if (layer.name === 'near') {
        ctx.drawImage(img, Math.round(cam), 0, FD.VIEW_W, FD.VIEW_H, 0, 0, FD.VIEW_W, FD.VIEW_H);
        continue;
      }
      const off = ((cam * layer.parallax) % img.width + img.width) % img.width;
      const x0 = -Math.round(off);
      for (let x = x0; x < FD.VIEW_W; x += img.width) {
        ctx.drawImage(img, x, 0);
      }
    }
    // sodium lamp pools on the sidewalk (additive)
    const pool = FD.assets.img('stage/props/light_pool.png');
    if (pool) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (const lx of [240, 700, 1160, 1620]) {
        const sx = lx - cam;
        if (sx < -60 || sx > FD.VIEW_W + 60) continue;
        const flicker = 0.55 + 0.06 * Math.sin(game.tick * 0.11 + lx);
        ctx.globalAlpha = flicker * 0.5;
        ctx.drawImage(pool, sx - 48, 168, 96, 96);
      }
      ctx.restore();
    }
  }

  function drawRain(game, ctx) {
    const w = FD.cfg.presentation.weather;
    ctx.save();
    ctx.strokeStyle = 'rgba(150,190,230,0.30)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (const d of game.rain) {
      const dx = d.len * w.rainAngle;
      ctx.moveTo(d.x, d.y);
      ctx.lineTo(d.x + dx, d.y + d.len);
    }
    ctx.stroke();
    ctx.fillStyle = 'rgba(170,210,240,0.45)';
    for (const s of game.splashes) {
      const a = 1 - s.t / s.life;
      ctx.globalAlpha = a * 0.7;
      ctx.fillRect(Math.round(s.x), Math.round(s.y), 2, 1);
    }
    ctx.restore();
    if (game.lightning.flash > 0) {
      const a = (game.lightning.flash / 12) * 0.35;
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      ctx.fillStyle = `rgba(180,200,255,${a})`;
      ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
      ctx.restore();
    }
  }

  function drawShadow(ctx, actor) {
    const baseY = actor.z + 1;
    const scale = 1 - (actor.yOffset || 0) / 90;
    const w = 22 * Math.max(0.4, scale);
    ctx.save();
    ctx.globalAlpha = actor.state === 'defeated' ? 0.14 : 0.32 * Math.max(0.4, scale);
    ctx.fillStyle = '#05060c';
    ctx.beginPath();
    ctx.ellipse(actor.x - gameCamX + 0, baseY, w, 4.2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  let gameCamX = 0;

  function drawActor(game, ctx, actor) {
    const cfg = FD.characterCfg(actor.charId);
    if (!cfg) return;
    const animDef = cfg.animations[actor.anim];
    if (!animDef) return;
    const frame = Math.min(actor.frame, animDef.frames.length - 1);
    const sheet = actor.sheet || actor.charId;
    const rel = `characters/${sheet}/frames/${actor.anim}/${actor.anim}_${String(frame).padStart(2, '0')}.png`;
    const img = FD.assets.img(rel);
    if (!img) return;
    const ax = cfg.frame.anchorX;
    const ay = cfg.frame.anchorY;
    const sx = Math.round(actor.x - gameCamX - ax);
    const sy = Math.round(actor.z - ay - (actor.yOffset || 0));
    const scale = actor.drawScale && actor.drawScale !== 1 ? actor.drawScale : 1;
    ctx.save();
    if (actor.alpha !== undefined && actor.alpha < 1) ctx.globalAlpha = actor.alpha;
    if (scale !== 1 || actor.facing < 0) {
      // Scale and flip around the frame anchor so the feet stay planted.
      ctx.translate(actor.x - gameCamX, actor.z - (actor.yOffset || 0));
      ctx.scale(scale * (actor.facing < 0 ? -1 : 1), scale);
      ctx.drawImage(img, -ax, -ay);
    } else {
      ctx.drawImage(img, sx, sy);
    }
    ctx.restore();
    const flashColor = actor.flash > 0 ? (actor.kind === 'player' ? '#ffffff' : '#ffd9d0') : null;
    const isElite = actor.type === 'rivet_elite';
    if (flashColor || isElite) {
      const sil = silhouette(img, flashColor || '#ff8a6a');
      if (sil) {
        ctx.save();
        // Two-stage hit flash: two bright ticks on contact, then a faint tint
        // for the rest of the flinch. A constant bright overlay erased the
        // sprite silhouette for 6 ticks, which looked like a rendering bug.
        ctx.globalAlpha = flashColor ? (actor.flash >= 5 ? 0.55 : 0.16) : 0.24;
        if (actor.alpha !== undefined && actor.alpha < 1) ctx.globalAlpha *= actor.alpha;
        if (scale !== 1 || actor.facing < 0) {
          ctx.translate(actor.x - gameCamX, actor.z - (actor.yOffset || 0));
          ctx.scale(scale * (actor.facing < 0 ? -1 : 1), scale);
          ctx.drawImage(sil, -ax, -ay);
        } else {
          ctx.drawImage(sil, sx, sy);
        }
        ctx.restore();
      }
    }
    if (FD.cfg.presentation.debug.showHitboxes) {
      drawHitboxes(game, ctx, actor);
    }
  }

  function drawHitboxes(game, ctx, actor) {
    const A = FD.Actors;
    const hb = A.hurtBoxFor(actor);
    ctx.save();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(90,255,140,0.8)';
    ctx.strokeRect(hb.x - gameCamX, hb.y, hb.w, hb.h);
    const hit = A.currentFrame(actor) && A.currentFrame(actor).hit;
    if (hit) {
      const box = A.hitBoxFor(actor, hit, 3);
      ctx.strokeStyle = 'rgba(255,90,90,0.9)';
      ctx.strokeRect(box.x - gameCamX, box.y, box.w, box.h);
    }
    ctx.restore();
  }

  function drawEffects(game, ctx, front) {
    for (const fx of game.effects) {
      const t = fx.t / fx.life;
      const sx = fx.x - gameCamX;
      if (front === false && fx.type === 'spawn') continue;
      ctx.save();
      if (fx.type === 'hit') {
        const a = 1 - t;
        ctx.globalAlpha = a;
        ctx.strokeStyle = fx.color || '#ffffff';
        ctx.lineWidth = 2;
        const r = 8 + t * 16;
        for (let i = 0; i < 6; i++) {
          const ang = (i / 6) * Math.PI * 2 + fx.dir * 0.4;
          ctx.beginPath();
          ctx.moveTo(sx + Math.cos(ang) * 4, fx.y + Math.sin(ang) * 4);
          ctx.lineTo(sx + Math.cos(ang) * r, fx.y + Math.sin(ang) * r);
          ctx.stroke();
        }
        ctx.globalCompositeOperation = 'lighter';
        ctx.fillStyle = fx.color || '#ffffff';
        ctx.globalAlpha = a * 0.8;
        ctx.beginPath();
        ctx.arc(sx, fx.y, 3 + t * 6, 0, Math.PI * 2);
        ctx.fill();
      } else if (fx.type === 'damage' || fx.type === 'text') {
        const rise = FD.ease.outCubic(Math.min(1, t * 1.4)) * 18;
        FD.font.draw(ctx, fx.text, sx, fx.y - rise, {
          color: fx.color || 'cyan', align: 'center', scale: 1,
          alpha: 1 - Math.max(0, t - 0.6) / 0.4,
        });
      } else if (fx.type === 'ko') {
        FD.font.draw(ctx, 'K.O.', sx, fx.y - t * 10, {
          color: 'amber', align: 'center', scale: 2, alpha: 1 - Math.max(0, t - 0.5) / 0.5,
        });
      } else if (fx.type === 'shockwave') {
        ctx.globalCompositeOperation = 'lighter';
        const r = 10 + FD.ease.outCubic(t) * 66;
        ctx.strokeStyle = `rgba(99,247,255,${0.8 * (1 - t)})`;
        ctx.lineWidth = 3 * (1 - t) + 1;
        ctx.beginPath();
        ctx.ellipse(sx, fx.y, r, r * 0.42, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.strokeStyle = `rgba(255,255,255,${0.5 * (1 - t)})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.ellipse(sx, fx.y, r * 0.72, r * 0.3, 0, 0, Math.PI * 2);
        ctx.stroke();
      } else if (fx.type === 'dust') {
        ctx.globalAlpha = 1 - t;
        ctx.fillStyle = '#8e93a8';
        for (let i = 0; i < 5; i++) {
          const dir = i < 2 ? -1 : 1;
          const px = sx + dir * (4 + t * 14 + i * 2);
          const py = fx.y - t * 8 - (i % 2) * 3;
          ctx.fillRect(Math.round(px), Math.round(py), 2, 2);
        }
      } else if (fx.type === 'debris' || fx.type === 'break') {
        ctx.globalAlpha = 1 - t;
        ctx.fillStyle = fx.color || '#7a5230';
        for (let i = 0; i < 9; i++) {
          const ang = (i / 9) * Math.PI * 2;
          const r = t * (fx.type === 'break' ? 26 : 14);
          ctx.fillRect(Math.round(sx + Math.cos(ang) * r), Math.round(fx.y + Math.sin(ang) * r * 0.7 + t * t * 16), 2, 2);
        }
      } else if (fx.type === 'spawn') {
        ctx.globalCompositeOperation = 'lighter';
        ctx.globalAlpha = (1 - t) * 0.7;
        ctx.fillStyle = '#ff6a4a';
        ctx.beginPath();
        ctx.ellipse(sx, fx.y, 12 + t * 18, 4 + t * 6, 0, 0, Math.PI * 2);
        ctx.fill();
      } else if (fx.type === 'heal') {
        ctx.globalAlpha = 1 - t;
        FD.font.draw(ctx, 'CHARGE', sx, fx.y - t * 24, { color: 'green', align: 'center', alpha: 1 - t });
      } else if (fx.type === 'block') {
        ctx.globalAlpha = 1 - t;
        ctx.strokeStyle = '#9ff6ff';
        ctx.strokeRect(sx - 10, fx.y - 6, 20, 12);
      }
      ctx.restore();
    }
  }

  // ------------------------------------------------------------------ HUD
  function drawBar(ctx, x, y, w, h, ratio, color, bg = '#101826') {
    ctx.fillStyle = bg;
    ctx.fillRect(x - 1, y - 1, w + 2, h + 2);
    ctx.fillStyle = '#2a3348';
    ctx.fillRect(x, y, w, h);
    ctx.fillStyle = color;
    ctx.fillRect(x, y, Math.round(w * FD.clamp(ratio, 0, 1)), h);
    ctx.fillStyle = 'rgba(255,255,255,0.22)';
    ctx.fillRect(x, y, Math.round(w * FD.clamp(ratio, 0, 1)), 1);
  }

  function drawHUD(game, ctx) {
    const p = game.player;
    const combat = FD.cfg.combat.player;
    // portrait + health
    const portrait = FD.assets.img('ui/portrait_frame.png');
    if (portrait) ctx.drawImage(portrait, 8, 8);
    const face = FD.assets.img('characters/volt/frames/idle/idle_00.png');
    if (face) {
      // crop the head (frame space around x=57 y=32) and scale it 2x into the badge
      ctx.save();
      ctx.beginPath();
      ctx.rect(11, 11, 28, 28);
      ctx.clip();
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(face, 43, 16, 28, 28, 11, 11, 28, 28);
      ctx.restore();
    }
    FD.font.draw(ctx, 'VOLT', 46, 9, { color: 'white', scale: 1 });
    const hpRatio = p.health / p.maxHealth;
    drawBar(ctx, 46, 20, 96, 5, hpRatio, hpRatio > 0.35 ? '#63f7ff' : '#ff5a52');
    drawBar(ctx, 46, 28, 84, 2, 1 - p.specialCooldown / combat.special.cooldownTicks, '#ffbe5c');
    FD.font.draw(ctx, 'HP', 148, 19, { color: 'dim', scale: 1 });
    // score + time
    FD.font.draw(ctx, 'SCORE', 424, 9, { color: 'dim', align: 'right' });
    FD.font.draw(ctx, FD.pad(game.score, 6), 424, 18, { color: 'white', align: 'right' });
    FD.font.draw(ctx, 'TIME', 424, 30, { color: 'dim', align: 'right' });
    FD.font.draw(ctx, FD.pad(Math.ceil(game.timerTicks / 60), 2), 424, 39, { color: 'amber', align: 'right' });
    // stage label
    FD.font.draw(ctx, FD.cfg.stage.title, 240, 9, { color: 'cyanDim', align: 'center', scale: 1 });

    // enemy health bars
    if (FD.cfg.presentation.ui.enemyHealthBars) {
      for (const e of game.enemies) {
        if (e.state === 'defeated' || e.health >= e.maxHealth) continue;
        const sx = e.x - gameCamX;
        if (sx < 0 || sx > FD.VIEW_W) continue;
        const y = e.z - 74;
        const barColor = e.boss ? '#ffd24a' : e.def && e.def.elite ? '#ff8a6a' : '#ff5cc4';
        drawBar(ctx, sx - 14, y, e.boss ? 40 : 28, e.boss ? 3 : 2, e.health / e.maxHealth, barColor);
      }
    }
    // combo
    if (game.combo.count > 1 && game.combo.timer > 0) {
      FD.font.draw(ctx, `${game.combo.count} HIT`, 12, 232, { color: 'amber', scale: 2 });
      FD.font.draw(ctx, 'COMBO', 12, 250, { color: 'dim' });
    }
    // banners
    if (game.stageState && game.stageState.bannerTicks > 0) {
      const tt = 120 - game.stageState.bannerTicks;
      const alpha = FD.clamp(Math.min(tt / 12, game.stageState.bannerTicks / 24), 0, 1);
      if (game.stageState.banner) {
        FD.font.draw(ctx, game.stageState.banner, 240, 112, {
          color: 'amber', scale: 2, align: 'center', alpha,
        });
      }
    }
  }

  function drawVignette(game, ctx) {
    if (!FD.cfg.presentation.render.vignette) return;
    if (!game.vignette) {
      const g = ctx.createRadialGradient(240, 135, 90, 240, 135, 300);
      g.addColorStop(0, 'rgba(0,0,0,0)');
      g.addColorStop(1, 'rgba(2,4,10,0.55)');
      game.vignette = g;
    }
    ctx.fillStyle = game.vignette;
    ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
    if (FD.cfg.presentation.render.scanlines && game.scanPattern) {
      ctx.save();
      ctx.globalAlpha = 0.5;
      ctx.fillStyle = game.scanPattern;
      ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
      ctx.restore();
    }
  }

  // ------------------------------------------------------------------ frame
  R.draw = function (game) {
    const ctx = game.ctx;
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, FD.VIEW_W, FD.VIEW_H);
    gameCamX = game.camera.x;

    const shake = game.shake;
    const sx = shake > 0.1 ? (Math.random() * 2 - 1) * shake : 0;
    const sy = shake > 0.1 ? (Math.random() * 2 - 1) * shake * 0.7 : 0;
    ctx.save();
    ctx.translate(Math.round(sx), Math.round(sy));
    drawBackdrop(game, ctx);

    // drawable list sorted by depth (feet y), props included
    const drawables = [];
    for (const prop of game.props) {
      if (prop.broken) continue;
      drawables.push({ z: prop.z, kind: 'prop', ref: prop });
    }
    for (const pick of game.pickups) {
      drawables.push({ z: pick.z, kind: 'pickup', ref: pick });
    }
    if (!game.player.hidden && game.player.state !== 'dead') {
      drawables.push({ z: game.player.z, kind: 'actor', ref: game.player });
    } else if (game.player.state === 'dead') {
      drawables.push({ z: game.player.z, kind: 'actor', ref: game.player });
    }
    for (const e of game.enemies) drawables.push({ z: e.z, kind: 'actor', ref: e });
    drawables.sort((a, b) => a.z - b.z);

    for (const d of drawables) {
      if (d.kind === 'actor') {
        drawShadow(ctx, d.ref);
      }
    }
    for (const d of drawables) {
      if (d.kind === 'prop') {
        const prop = d.ref;
        const meta = FD.assets.dataRef ? null : null;
        const frames = { crate: 2, barrel: 2, trash: 2 }[prop.type] || 1;
        const stageIdx = prop.hp <= prop.maxHp / 2 && frames > 1 ? 1 : 0;
        const img = FD.assets.img(`stage/props/${prop.type}_${stageIdx}.png`);
        if (img) {
          const x = Math.round(prop.x - gameCamX - prop.w / 2);
          const y = Math.round(prop.z - prop.h);
          if (prop.hitFlash > 0) {
            ctx.save();
            ctx.globalAlpha = 0.9;
            ctx.drawImage(img, x, y);
            const sil = silhouette(img, '#ffffff');
            if (sil) {
              ctx.globalAlpha = 0.7;
              ctx.drawImage(sil, x, y);
            }
            ctx.restore();
          } else {
            ctx.drawImage(img, x, y);
          }
          if (FD.cfg.presentation.debug.showHitboxes) {
            const b = prop.box();
            ctx.strokeStyle = 'rgba(255,200,80,0.9)';
            ctx.strokeRect(b.x - gameCamX, b.y, b.w, b.h);
          }
        }
      } else if (d.kind === 'pickup') {
        const pick = d.ref;
        const img = FD.assets.img(`stage/props/pickup_${pick.type}.png`);
        if (img) {
          const bob = Math.sin(pick.bob) * 2;
          const blink = pick.ttl < 120 && Math.floor(pick.ttl / 6) % 2 === 0;
          if (!blink) {
            ctx.save();
            ctx.globalCompositeOperation = 'lighter';
            ctx.globalAlpha = 0.28 + Math.sin(pick.bob * 1.3) * 0.08;
            ctx.fillStyle = pick.type === 'health' ? '#63f7ff' : '#ffbe5c';
            ctx.beginPath();
            ctx.arc(pick.x - gameCamX, pick.z - 14 + bob, 12, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
            ctx.drawImage(img, Math.round(pick.x - gameCamX - 9), Math.round(pick.z - 22 + bob));
          }
        }
      } else {
        drawActor(game, ctx, d.ref);
      }
    }

    drawEffects(game, ctx, true);
    ctx.restore();

    drawRain(game, ctx);
    drawVignette(game, ctx);

    // HUD is drawn without shake so text stays readable
    if (game.state === 'playing' || game.state === 'paused' || game.state === 'stageclear') {
      drawHUD(game, ctx);
    }

    if (game.hitstop > 0 && FD.cfg.presentation.render.flashAlpha > 0) {
      // subtle white frame on impact
      ctx.save();
      ctx.globalAlpha = 0.06;
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
      ctx.restore();
    }

    game.shake *= FD.cfg.presentation.render.screenShakeDecay;
    if (game.shake < 0.08) game.shake = 0;
  };

  FD.Renderer = R;
})();
