// Actor state machines: player (VOLT) and the RIVET enemy archetypes.
// All timing comes from config/animation.json, all numbers from the config
// bundle.  Nothing here is hard-coded per animation frame.
(function () {
  'use strict';
  const FD = window.FD;
  const A = {};

  // ------------------------------------------------------------------ helpers
  function charCfg(charId) {
    return FD.characterCfg(charId);
  }
  function animCfg(charId, anim) {
    const c = charCfg(charId);
    return c ? c.animations[anim] : null;
  }
  function frameCount(charId, anim) {
    const a = animCfg(charId, anim);
    return a ? a.frames.length : 1;
  }
  A.frameCount = frameCount;

  function setAnim(actor, name, resetHitSet = true) {
    const def = animCfg(actor.charId, name);
    if (!def) throw new Error(`missing animation ${actor.charId}/${name}`);
    actor.anim = name;
    actor.frame = 0;
    actor.frameTicks = 0;
    actor.animTicks = 0;
    if (resetHitSet) actor.hitSet.clear();
    return def;
  }
  A.setAnim = setAnim;

  // Advances the animation clock. Returns true when a non-looping animation
  // has just finished.
  function advanceAnim(actor, ticks = 1) {
    const def = animCfg(actor.charId, actor.anim);
    if (!def) return true;
    for (let i = 0; i < ticks; i++) {
      actor.animTicks += 1;
      actor.frameTicks += 1;
      const frame = def.frames[actor.frame];
      if (actor.frameTicks >= frame.dur) {
        actor.frameTicks = 0;
        if (actor.frame + 1 < def.frames.length) {
          actor.frame += 1;
        } else if (def.loop) {
          actor.frame = 0;
        } else if (def.hold) {
          actor.frame = def.frames.length - 1;
          return true;
        } else {
          actor.finished = true;
          return true;
        }
      }
    }
    return false;
  }
  A.advanceAnim = advanceAnim;

  function currentFrame(actor) {
    const def = animCfg(actor.charId, actor.anim);
    return def ? def.frames[Math.min(actor.frame, def.frames.length - 1)] : null;
  }
  A.currentFrame = currentFrame;

  function activeHit(actor) {
    const f = currentFrame(actor);
    return f && f.hit ? f.hit : null;
  }

  // World-space attack box for the current frame.
  function hitBoxFor(actor, rect, depthBonus = 0) {
    const halfDepth = (actor.depthTolerance || 14) + depthBonus;
    const top = actor.z - actor.yOffset + rect.y;
    if (actor.facing >= 0) {
      return { x: actor.x + rect.x, y: top, w: rect.w, h: rect.h, zMin: actor.z - halfDepth, zMax: actor.z + halfDepth };
    }
    return { x: actor.x - rect.x - rect.w, y: top, w: rect.w, h: rect.h, zMin: actor.z - halfDepth, zMax: actor.z + halfDepth };
  }
  A.hitBoxFor = hitBoxFor;

  function hurtBoxFor(actor) {
    const c = FD.cfg.collision[actor.kind === 'player' ? 'player' : 'enemy'];
    const top = actor.z - actor.yOffset - c.bodyHeight;
    return {
      x: actor.x - c.bodyWidth / 2, y: top, w: c.bodyWidth, h: c.bodyHeight,
      zMin: actor.z - c.depthTolerance, zMax: actor.z + c.depthTolerance,
    };
  }
  A.hurtBoxFor = hurtBoxFor;

  function boxesOverlap(a, b) {
    if (!FD.rectsOverlap(a, b)) return false;
    return a.zMin <= b.zMax && a.zMax >= b.zMin;
  }
  A.boxesOverlap = boxesOverlap;

  function depthDistance(a, b) {
    return Math.abs(a.z - b.z);
  }

  // ------------------------------------------------------------------ player
  A.createPlayer = function (game, x, z) {
    const combat = FD.cfg.combat.player;
    const mv = FD.cfg.movement.player;
    const col = FD.cfg.collision.player;
    const p = {
      kind: 'player', charId: 'volt', id: 'player',
      x, z, facing: 1,
      state: 'idle', anim: 'idle', frame: 0, frameTicks: 0, animTicks: 0,
      health: combat.maxHealth, maxHealth: combat.maxHealth,
      vx: 0, vz: 0, vy: 0, yOffset: 0,
      invulnTicks: 0, hurtTicks: 0, knockdownTicks: 0,
      specialCooldown: 0, specialSpent: false, attackBuffer: 0, comboIndex: 0, attackId: null,
      attackTicks: 0, chainAtTick: 0, dead: false, hidden: false,
      depthTolerance: col.depthTolerance, bodyWidth: col.bodyWidth, bodyHeight: col.bodyHeight,
      hitSet: new Set(), propHitSet: new Set(),
      spawnGrace: 0, flash: 0, lastAttackLanded: false,
    };
    setAnim(p, 'idle');
    return p;
  };

  function startPlayerAttack(game, p, index) {
    const name = 'attack' + (index + 1);
    const def = FD.cfg.combat.player.attacks[name];
    if (!def) return;
    setAnim(p, name);
    p.state = 'attack';
    p.comboIndex = index;
    p.attackId = name;
    p.attackTicks = 0;
    p.attackBuffer = 0;
    p.lastAttackLanded = false;
    p.propHitSet.clear();
    const frames = animCfg('volt', name).frames;
    let lastHit = 0;
    let t = 0;
    frames.forEach((f) => {
      if (f.hit) lastHit = t + f.dur;
      t += f.dur;
    });
    p.chainAtTick = lastHit;
    p.vx = p.facing * 0.55 * (index === 2 ? 2.2 : 1);
    FD.sfx('whoosh', { volume: 0.25 });
  }

  function startPlayerJump(game, p) {
    const mv = FD.cfg.movement.player;
    p.state = 'jump';
    setAnim(p, 'jump');
    p.vy = Math.abs(mv.jumpVelocity);
    p.yOffset = 0.01;
    p.vx = p.facing * Math.abs(mv.walkSpeed) * 0.92;
    p.vz = p.vz * 0.5;
    FD.sfx('land', { volume: 0.3, rate: 1.6 });
  }

  function startPlayerSpecial(game, p) {
    const sp = FD.cfg.combat.player.special;
    if (p.specialCooldown > 0) return;
    setAnim(p, 'special');
    p.state = 'special';
    p.attackId = 'special';
    p.specialCooldown = sp.cooldownTicks;
    p.invulnTicks = Math.max(p.invulnTicks, sp.invulnTicks);
    p.hitSet.clear();
    p.propHitSet.clear();
    p.specialSpent = false;
    p.vx = 0;
    p.vz = 0;
    game.addEffect({ type: 'shockwave', x: p.x, y: p.z, t: 0, life: 26, facing: p.facing });
    FD.sfx('zap');
    game.audioKick = true;
  }

  // SoR1-style special: the health is only paid when the move connects, the
  // cost is charged once per special (not per target), and it can never kill.
  function spendSpecialCost(game, p) {
    if (p.specialSpent) return;
    p.specialSpent = true;
    const sp = FD.cfg.combat.player.special;
    const cost = sp.healthCost || 0;
    if (!cost) return;
    const before = p.health;
    p.health = Math.max(1, p.health - cost);
    const paid = before - p.health;
    if (paid > 0) {
      game.addEffect({ type: 'damage', x: p.x, y: p.z - 74, t: 0, life: 34, text: `-${paid}`, color: 'red' });
    }
  }

  function playerTakeHit(game, p, amount, opts = {}) {
    if (p.invulnTicks > 0 || p.dead || game.debug.invincible) {
      game.addEffect({ type: 'block', x: p.x, y: p.z - 40, t: 0, life: 10 });
      return false;
    }
    p.health = Math.max(0, p.health - amount);
    if (game.stats) game.stats.damageTaken += amount;
    p.invulnTicks = FD.cfg.combat.player.hurtInvulnTicks;
    p.flash = 6;
    game.hitstop = Math.max(game.hitstop, 3);
    game.shake = Math.max(game.shake, 2.2);
    FD.sfx('hurt');
    game.addEffect({ type: 'hit', x: p.x, y: p.z - 42, t: 0, life: 14, color: '#ff5a52', dir: opts.dir || -p.facing });
    game.addEffect({ type: 'damage', x: p.x, y: p.z - 62, t: 0, life: 38, text: String(amount), color: 'red' });
    if (p.health <= 0) {
      p.dead = true;
      p.state = 'fall';
      setAnim(p, 'fall');
      p.vy = 2.6;
      p.vx = (opts.dir || -p.facing) * 1.4;
      p.knockdownTicks = FD.cfg.combat.player.knockdownTicks;
      FD.sfx('punch_heavy');
      return true;
    }
    if (opts.knockdown) {
      p.state = 'fall';
      setAnim(p, 'fall');
      p.vy = 2.2;
      p.vx = (opts.dir || -p.facing) * Math.max(1.5, opts.knockback || 2);
      p.knockdownTicks = FD.cfg.combat.player.knockdownTicks;
    } else {
      p.state = 'hurt';
      setAnim(p, 'hurt');
      p.hurtTicks = FD.cfg.combat.player.hurtTicks;
      p.vx = (opts.dir || -p.facing) * (opts.knockback || 1.2);
    }
    return true;
  }

  A.updatePlayer = function (game, p) {
    const input = FD.input;
    const mv = FD.cfg.movement.player;
    const combat = FD.cfg.combat.player;
    const arena = game.arena();

    p.attackBuffer = Math.max(0, p.attackBuffer - 1);
    p.invulnTicks = Math.max(0, p.invulnTicks - 1);
    p.specialCooldown = Math.max(0, p.specialCooldown - 1);
    p.flash = Math.max(0, p.flash - 1);

    const grounded = p.yOffset <= 0 && p.state !== 'jump' && p.state !== 'jump_attack';

    // ---- incapacitated states
    if (p.state === 'dead') {
      p.vx = FD.approach(p.vx, 0, 0.12);
      p.x = FD.clamp(p.x + p.vx, arena.minX, arena.maxX);
      return;
    }
    if (p.state === 'hurt') {
      p.hurtTicks -= 1;
      p.vx = FD.approach(p.vx, 0, 0.22);
      p.x = FD.clamp(p.x + p.vx, arena.minX, arena.maxX);
      advanceAnim(p);
      if (p.hurtTicks <= 0) {
        p.state = 'idle';
        setAnim(p, 'idle');
      }
      return;
    }
    if (p.state === 'fall') {
      // airborne knockback, then lie on the floor
      if (p.yOffset > 0 || p.vy > 0) {
        p.vy -= FD.cfg.movement.player.gravity;
        p.yOffset += p.vy;
        p.x = FD.clamp(p.x + p.vx, arena.minX, arena.maxX);
        p.vx = FD.approach(p.vx, 0, 0.06);
        if (p.yOffset <= 0) {
          p.yOffset = 0;
          p.vy = 0;
          p.vx = 0;
          game.shake = Math.max(game.shake, 2.4);
          FD.sfx('land', { volume: 0.5 });
          game.addEffect({ type: 'dust', x: p.x, y: p.z, t: 0, life: 16 });
        }
        advanceAnim(p);
      } else {
        p.knockdownTicks -= 1;
        p.yOffset = 0;
        advanceAnim(p);
        if (p.knockdownTicks <= 0) {
          if (p.dead) {
            p.state = 'dead';
            advanceAnim(p);
            p.frame = frameCount('volt', 'fall') - 1;
            game.onPlayerDead();
          } else {
            p.state = 'getup';
            setAnim(p, 'getup');
            p.invulnTicks = Math.max(p.invulnTicks, combat.getupInvulnTicks);
            FD.sfx('select', { volume: 0.35 });
          }
        }
      }
      return;
    }
    if (p.state === 'getup') {
      if (advanceAnim(p)) {
        p.state = 'idle';
        setAnim(p, 'idle');
      }
      return;
    }
    if (p.state === 'victory') {
      advanceAnim(p);
      return;
    }

    // ---- attacks
    if (p.state === 'attack' || p.state === 'special') {
      p.attackTicks += 1;
      p.vx = FD.approach(p.vx, 0, 0.1);
      p.x = FD.clamp(p.x + p.vx, arena.minX, arena.maxX);
      if (p.state === 'attack' && input.wasPressed('attack')) {
        p.attackBuffer = combat.attackBufferTicks;
      }
      const finished = advanceAnim(p);
      if (p.state === 'attack' && p.attackBuffer > 0 && p.comboIndex < 2 && p.attackTicks >= p.chainAtTick) {
        startPlayerAttack(game, p, p.comboIndex + 1);
        return;
      }
      if (finished) {
        p.state = 'idle';
        setAnim(p, 'idle');
      }
      return;
    }

    // ---- air states
    if (p.state === 'jump' || p.state === 'jump_attack') {
      const g = FD.cfg.movement.player.gravity;
      p.vy -= g;
      p.yOffset += p.vy;
      p.x = FD.clamp(p.x + p.vx, arena.minX, arena.maxX);
      if (p.state === 'jump') {
        if (input.wasPressed('attack') || input.wasPressed('special')) {
          p.state = 'jump_attack';
          setAnim(p, 'jump_attack');
          p.attackId = 'jump_attack';
          p.propHitSet.clear();
          p.hitSet.clear();
          p.vx = p.facing * 1.1;
          FD.sfx('whoosh', { volume: 0.3 });
        } else {
          const f = p.vy > 1.2 ? 1 : p.vy > -1.2 ? 2 : 3;
          p.frame = Math.min(f, frameCount('volt', 'jump') - 1);
        }
      } else {
        advanceAnim(p);
      }
      if (p.yOffset <= 0) {
        p.yOffset = 0;
        p.vy = 0;
        p.state = 'land';
        setAnim(p, 'idle');
        p.frame = 0;
        p.landTicks = mv.landRecoveryTicks;
        game.addEffect({ type: 'dust', x: p.x, y: p.z, t: 0, life: 14 });
        FD.sfx('land');
      }
      return;
    }
    if (p.state === 'land') {
      p.landTicks -= 1;
      p.vx = FD.approach(p.vx, 0, 0.3);
      p.x = FD.clamp(p.x + p.vx, arena.minX, arena.maxX);
      if (p.landTicks <= 0) {
        p.state = 'idle';
        setAnim(p, 'idle');
      }
      return;
    }

    // ---- free movement
    const ax = input.axisX();
    const ay = input.axisY();
    if (input.wasPressed('special') && p.specialCooldown <= 0) {
      startPlayerSpecial(game, p);
      return;
    }
    if (input.wasPressed('attack')) {
      startPlayerAttack(game, p, 0);
      return;
    }
    if (input.wasPressed('jump')) {
      startPlayerJump(game, p);
      return;
    }

    if (ax !== 0) {
      p.facing = ax;
      p.vx = FD.approach(p.vx, ax * mv.walkSpeed, mv.accel);
    } else {
      p.vx = FD.approach(p.vx, 0, mv.decel);
    }
    p.vz = FD.approach(p.vz, ay * mv.depthSpeed, mv.accel * 1.15);
    p.x = FD.clamp(p.x + p.vx, arena.minX, arena.maxX);
    p.z = FD.clamp(p.z + p.vz, FD.cfg.stage.laneMin, FD.cfg.stage.laneMax);

    const moving = Math.abs(p.vx) > 0.15 || Math.abs(p.vz) > 0.15;
    if (moving) {
      if (p.state !== 'walk') {
        p.state = 'walk';
        setAnim(p, 'walk');
      } else {
        advanceAnim(p);
      }
    } else {
      if (p.state !== 'idle') {
        p.state = 'idle';
        setAnim(p, 'idle');
      } else {
        advanceAnim(p);
      }
    }
  };

  // ------------------------------------------------------------------ enemy
  A.createEnemy = function (game, type, x, z, opts = {}) {
    const def = FD.cfg.combat.enemyTypes[type];
    if (!def) throw new Error('unknown enemy type ' + type);
    const col = FD.cfg.collision.enemy;
    const st = FD.cfg.stage || {};
    const hpMul = opts.healthMul || st.enemyHealthMul || 1;
    const dmgMul = opts.damageMul || st.enemyDamageMul || 1;
    const maxHealth = Math.max(1, Math.round(def.maxHealth * hpMul));
    const sheet = def.elite ? 'rivet_elite' : (type === 'rivet' ? 'rivet' : type);
    const e = {
      kind: 'enemy', charId: type === 'rivet_elite' ? 'rivet_elite' : 'rivet', sheet, type, id: opts.id || `e${Math.random().toString(36).slice(2, 7)}`,
      x, z, facing: -1,
      state: 'spawn', anim: 'walk', frame: 0, frameTicks: 0, animTicks: 0,
      health: maxHealth, maxHealth,
      vx: 0, vz: 0, vy: 0, yOffset: 0,
      def, invulnTicks: 0, hurtTicks: 0, knockdownTicks: 0, cooldown: opts.cooldown || 30,
      decisionTicks: 0, side: opts.side || (x < game.player.x ? -1 : 1),
      attackId: null, attackTicks: 0, dead: false, defeatedTicks: 0,
      depthTolerance: col.depthTolerance, bodyWidth: col.bodyWidth, bodyHeight: col.bodyHeight,
      drawScale: def.drawScale || 1, boss: !!def.boss,
      attackDamage: Math.max(1, Math.round(def.attackDamage * dmgMul)),
      hitSet: new Set(), propHitSet: new Set(),
      flash: 0, spawnTicks: 0, alpha: 0, safeTime: 30,
      zJitter: (Math.random() * 2 - 1) * 5,
      retreatTicks: 0, lastAttackAt: -999,
    };
    setAnim(e, 'walk');
    return e;
  };

  function startEnemyAttack(game, e) {
    setAnim(e, 'attack');
    e.state = 'attack';
    e.attackId = 'enemy_attack';
    e.attackTicks = 0;
    e.lastAttackAt = game.tick;
    FD.sfx('whoosh', { volume: 0.22, rate: 0.8 });
  }

  function enemyTakeHit(game, e, damage, def, dir) {
    if (e.state === 'defeated' || e.state === 'fall') {
      // small chip damage while down is not allowed: keeps state machine simple
      return false;
    }
    e.health = Math.max(0, e.health - damage);
    e.flash = 6;
    e.invulnTicks = 4;
    game.addEffect({ type: 'hit', x: e.x, y: e.z - 44, t: 0, life: 14, color: '#8ff9ff', dir });
    game.addEffect({ type: 'damage', x: e.x, y: e.z - 64, t: 0, life: 40, text: String(damage), color: 'cyan' });
    game.hitstop = Math.max(game.hitstop, def.hitstop || 3);
    game.shake = Math.max(game.shake, def.shake || 1.4);
    if (def.sfx) FD.sfx(def.sfx);
    if (e.health <= 0) {
      e.state = 'fall';
      setAnim(e, 'fall');
      e.vy = 2.4;
      e.vx = dir * Math.max(1.4, def.knockback || 2);
      e.knockdownTicks = e.def.knockdownTicks;
      e.dying = true;
      if (game.stats) game.stats.enemiesDefeated += 1;
      game.addScore(e.def.score);
      game.addEffect({ type: 'ko', x: e.x, y: e.z - 70, t: 0, life: 46 });
    } else if (def.knockdown) {
      e.state = 'fall';
      setAnim(e, 'fall');
      e.vy = 2.0;
      e.vx = dir * (def.knockback || 2);
      e.knockdownTicks = e.def.knockdownTicks;
    } else {
      e.state = 'hurt';
      setAnim(e, 'hurt');
      e.hurtTicks = e.def.hurtTicks;
      e.vx = dir * (def.knockback || 1.2);
      e.cooldown = Math.max(e.cooldown, 18);
    }
    return true;
  }
  A.enemyTakeHit = enemyTakeHit;

  A.updateEnemy = function (game, e) {
    const arena = game.enemyArena();
    const p = game.player;
    e.flash = Math.max(0, e.flash - 1);
    e.invulnTicks = Math.max(0, e.invulnTicks - 1);
    e.safeTime = Math.max(0, e.safeTime - 1);
    e.cooldown = Math.max(0, e.cooldown - 1);
    e.decisionTicks = Math.max(0, e.decisionTicks - 1);

    if (e.state === 'defeated') {
      e.defeatedTicks += 1;
      e.alpha = FD.clamp(1 - e.defeatedTicks / 70, 0, 1);
      advanceAnim(e);
      return;
    }
    if (e.state === 'spawn') {
      e.spawnTicks += 1;
      e.alpha = FD.clamp(e.spawnTicks / 24, 0, 1);
      // walk in from outside the screen
      const dir = e.x > game.camera.x + 240 ? -1 : 1;
      e.facing = dir;
      e.x += dir * e.def.walkSpeed * 1.15;
      e.z = FD.approach(e.z, e.z + e.zJitter, 0.2);
      advanceAnim(e);
      const onScreen = e.x > game.camera.x + 24 && e.x < game.camera.x + 456;
      if (onScreen || e.spawnTicks > 140) {
        e.state = 'approach';
        e.decisionTicks = 0;
      }
      return;
    }
    if (e.state === 'hurt') {
      e.hurtTicks -= 1;
      e.vx = FD.approach(e.vx, 0, 0.22);
      e.x = FD.clamp(e.x + e.vx, arena.minX, arena.maxX);
      advanceAnim(e);
      if (e.hurtTicks <= 0) {
        e.state = 'approach';
        e.cooldown = Math.max(e.cooldown, 10);
      }
      return;
    }
    if (e.state === 'fall') {
      if (e.yOffset > 0 || e.vy > 0) {
        e.vy -= FD.cfg.movement.enemy.gravity;
        e.yOffset += e.vy;
        e.x = FD.clamp(e.x + e.vx, arena.minX, arena.maxX);
        e.vx = FD.approach(e.vx, 0, 0.05);
        if (e.yOffset <= 0) {
          e.yOffset = 0;
          e.vy = 0;
          e.vx = 0;
          game.addEffect({ type: 'dust', x: e.x, y: e.z, t: 0, life: 14 });
          FD.sfx('land', { volume: 0.35 });
        }
        advanceAnim(e);
      } else {
        e.knockdownTicks -= 1;
        advanceAnim(e);
        if (e.knockdownTicks <= 0) {
          if (e.dying) {
            e.state = 'defeated';
            e.defeatedTicks = 0;
            setAnim(e, 'defeated');
          } else {
            e.state = 'getup';
            setAnim(e, 'getup');
            e.invulnTicks = 46;
          }
        }
      }
      return;
    }
    if (e.state === 'getup') {
      if (advanceAnim(e)) {
        e.state = 'approach';
        e.cooldown = 24;
      }
      return;
    }
    if (e.state === 'attack') {
      e.attackTicks += 1;
      const finished = advanceAnim(e);
      if (finished) {
        e.state = 'approach';
        e.cooldown = e.def.attackCooldownTicks;
        if (Math.random() < e.def.retreatChance) {
          e.retreatTicks = 26;
          e.side = -e.side;
        }
      }
      return;
    }

    // ---- approach / idle
    if (e.state === 'idle') {
      e.decisionTicks -= 1;
      advanceAnim(e);
      if (e.decisionTicks <= 0) e.state = 'approach';
      return;
    }

    // approach: choose a side, keep spacing, attack when in range
    if (e.decisionTicks <= 0) {
      e.decisionTicks = 18 + Math.floor(Math.random() * 12);
      // flanking: if another enemy already holds this side, switch
      const sameSide = game.enemies.some(
        (o) => o !== e && o.state !== 'defeated' && Math.sign(o.x - p.x) === e.side && Math.abs(o.x - p.x) < 40
      );
      if (sameSide || e.x > game.camera.x + 470 || e.x < game.camera.x + 10) e.side = -e.side;
    }
    const targetX = p.x + e.side * e.def.preferredSideOffset;
    const targetZ = FD.clamp(p.z + e.def.preferredDepthOffset + e.zJitter, FD.cfg.stage.laneMin, FD.cfg.stage.laneMax);
    const retreating = e.retreatTicks > 0;
    e.retreatTicks = Math.max(0, e.retreatTicks - 1);
    const goalX = retreating ? p.x + e.side * (e.def.preferredSideOffset + 70) : targetX;
    const dx = goalX - e.x;
    const dz = targetZ - e.z;
    const speed = e.def.walkSpeed;
    const dspeed = e.def.depthSpeed;
    let moving = false;
    if (Math.abs(dx) > 3) {
      e.vx = FD.approach(e.vx, FD.sign(dx) * speed, 0.12);
      e.facing = p.x > e.x ? 1 : -1;
      moving = true;
    } else {
      e.vx = FD.approach(e.vx, 0, 0.16);
    }
    if (Math.abs(dz) > 1.5) {
      e.vz = FD.approach(e.vz, FD.sign(dz) * dspeed, 0.12);
      moving = true;
    } else {
      e.vz = FD.approach(e.vz, 0, 0.16);
    }
    e.x = FD.clamp(e.x + e.vx, arena.minX + 6, arena.maxX - 6);
    e.z = FD.clamp(e.z + e.vz, FD.cfg.stage.laneMin, FD.cfg.stage.laneMax);

    // keep a little personal space from other enemies
    for (const o of game.enemies) {
      if (o === e || o.state === 'defeated') continue;
      if (Math.abs(o.x - e.x) < 22 && Math.abs(o.z - e.z) < 12) {
        const push = (e.x < o.x ? -1 : 1) * 0.35;
        e.x += push;
        e.z += (e.z < o.z ? -1 : 1) * 0.18;
      }
    }

    if (moving) {
      if (e.anim !== 'walk') setAnim(e, 'walk');
      else advanceAnim(e);
    } else {
      if (e.anim !== 'idle') setAnim(e, 'idle');
      else advanceAnim(e);
    }

    // attack decision
    const inRange = Math.abs(p.x - e.x) <= e.def.attackRange + 6;
    const inDepth = Math.abs(p.z - e.z) <= (e.depthTolerance + 4);
    const playerVulnerable = !p.dead && p.state !== 'fall' && p.state !== 'getup' && p.yOffset < 26;
    if (inRange && inDepth && e.cooldown <= 0 && e.safeTime <= 0 && playerVulnerable &&
        game.tick - e.lastAttackAt > 24 && Math.random() < 0.5) {
      startEnemyAttack(game, e);
    }
  };

  // ------------------------------------------------------------------ combat pass
  A.resolveHits = function (game) {
    const p = game.player;
    const hits = [];

    // player -> enemies / props
    if (p.state === 'attack' || p.state === 'special' || p.state === 'jump_attack') {
      const hit = activeHit(p);
      if (hit) {
        const isSpecial = p.state === 'special' && hit.radial;
        if (isSpecial) {
          const sp = FD.cfg.combat.player.special;
          for (const e of game.enemies) {
            if (e.state === 'defeated' || e.state === 'fall') continue;
            if (p.hitSet.has(e.id)) continue;
            const dist = Math.abs(e.x - p.x);
            if (dist <= sp.radius && Math.abs(e.z - p.z) <= sp.depthRadius) {
              p.hitSet.add(e.id);
              if (enemyTakeHit(game, e, sp.damage, sp, FD.sign(e.x - p.x) || p.facing)) {
                game.onPlayerLandedHit(sp, e, isSpecial);
                spendSpecialCost(game, p);
              }
            }
          }
        } else {
          const def = FD.cfg.combat.player.attacks[p.attackId] || FD.cfg.combat.player.special;
          const box = hitBoxFor(p, hit, FD.cfg.collision.rules.attackDepthToleranceBonus);
          for (const e of game.enemies) {
            if (e.state === 'defeated' || e.state === 'fall') continue;
            if (p.hitSet.has(e.id)) continue;
            const hb = hurtBoxFor(e);
            if (boxesOverlap(box, hb)) {
              p.hitSet.add(e.id);
              if (enemyTakeHit(game, e, def.damage, def, FD.sign(e.x - p.x) || p.facing)) {
                game.onPlayerLandedHit(def, e, false);
              }
            }
          }
        }
        // props are hit by any attack frame with a rect (the special uses a radius too)
        for (const prop of game.props) {
          if (prop.broken || p.propHitSet.has(prop.id)) continue;
          const propBox = prop.box();
          let overlaps = false;
          if (isSpecial) {
            const sp = FD.cfg.combat.player.special;
            overlaps = Math.abs(prop.x - p.x) <= sp.radius && Math.abs(prop.z - p.z) <= sp.depthRadius + 6;
          } else {
            overlaps = boxesOverlap(hitBoxFor(p, hit, 6), propBox);
          }
          if (overlaps) {
            p.propHitSet.add(prop.id);
            game.hitProp(prop, isSpecial ? 2 : 1, FD.sign(prop.x - p.x) || p.facing);
            if (isSpecial) spendSpecialCost(game, p);
          }
        }
      }
    }

    // enemies -> player
    for (const e of game.enemies) {
      if (e.state !== 'attack') continue;
      const hit = activeHit(e);
      if (!hit) continue;
      if (e.hitSet.has('player')) continue;
      const box = hitBoxFor(e, hit, 4);
      const hb = hurtBoxFor(p);
      if (boxesOverlap(box, hb)) {
        e.hitSet.add('player');
        const def = { damage: e.attackDamage || e.def.attackDamage, knockdown: false, knockback: 1.4 };
        if (playerTakeHit(game, p, def.damage, { dir: FD.sign(p.x - e.x) || e.facing, knockback: def.knockback })) {
          game.combo.playerHits = 0;
        }
      }
    }
  };

  A.playerTakeHit = playerTakeHit;
  A.startPlayerAttack = startPlayerAttack;
  A.startPlayerSpecial = startPlayerSpecial;
  A.animCfg = animCfg;
  FD.Actors = A;
})();
