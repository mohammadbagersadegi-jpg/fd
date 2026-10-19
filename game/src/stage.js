// Stage flow: waves, props, pickups, camera and the arena bounds.
(function () {
  'use strict';
  const FD = window.FD;
  const S = {};

  S.init = function (game) {
    const st = FD.cfg.stage;
    game.stageState = {
      waveIndex: 0,
      waveActive: false,
      waveLockX: 0,
      clearedWaves: 0,
      pending: [],
      finished: false,
      finishBannerTicks: 0,
      banner: null,
      bannerTicks: 0,
    };
    game.camera.x = 0;
    game.camera.locked = false;
    game.props = st.props.map((p, i) => S.createProp(game, p, i));
    game.pickups = [];
    game.enemies = [];
    game.player = FD.Actors.createPlayer(game, st.startX, st.startZ);
    game.player.facing = 1;
    game.timerTicks = (st.timeLimitSeconds || 99) * 60;
    game.stageStartScore = game.score;
  };

  S.createProp = function (game, def, index) {
    const sizes = { crate: [34, 34], barrel: [26, 36], trash: [24, 30] };
    const [w, h] = sizes[def.type] || [30, 30];
    return {
      id: def.id || `prop_${index}`,
      type: def.type,
      x: def.x,
      z: def.z,
      w,
      h,
      hp: def.hp,
      maxHp: def.hp,
      broken: false,
      hitFlash: 0,
      drop: def.drop,
      box() {
        return {
          x: this.x - this.w / 2,
          y: this.z - this.h,
          w: this.w,
          h: this.h,
          zMin: this.z - FD.cfg.collision.prop.depthTolerance,
          zMax: this.z + FD.cfg.collision.prop.depthTolerance,
        };
      },
    };
  };

  S.spawnEnemy = function (game, def) {
    const st = FD.cfg.stage;
    const cam = game.camera.x;
    let x;
    if (def.spawnSide === 'left') x = cam - 30 - (def.spawnOffset || 0);
    else x = cam + 480 + 30 + (def.spawnOffset || 0) - 500; // offsets are tuned per spawn
    // spawnOffset is measured from the camera edge: right side => cam + 480 + offset
    if (def.spawnSide === 'right') x = cam + 480 + (def.spawnOffset || 40);
    const side = x > game.player.x ? 1 : -1;
    const e = FD.Actors.createEnemy(game, def.type, x, def.spawnZ, {
      side,
      healthMul: def.healthMul || st.enemyHealthMul,
      damageMul: def.damageMul || st.enemyDamageMul,
    });
    game.enemies.push(e);
    game.addEffect({ type: 'spawn', x: clampWorld(x), y: def.spawnZ, t: 0, life: 24 });
    return e;
  };

  function clampWorld(x) {
    return FD.clamp(x, 0, FD.cfg.stage.worldWidth);
  }

  S.update = function (game) {
    const st = FD.cfg.stage;
    const ss = game.stageState;
    const p = game.player;

    // ---- wave progression
    if (!ss.finished) {
      if (!ss.waveActive && ss.waveIndex < st.waves.length) {
        const wave = st.waves[ss.waveIndex];
        if (p.x >= wave.triggerX && p.state !== 'dead') {
          ss.waveActive = true;
          ss.waveLockX = game.camera.x;
          game.camera.locked = true;
          ss.banner = wave.banner || `WAVE ${ss.waveIndex + 1}`;
          ss.bannerTicks = 120;
          FD.sfx('select');
          for (const def of wave.enemies) {
            ss.pending.push({ def, delay: def.delay || 0 });
          }
        }
      }
      if (ss.waveActive) {
        for (let i = ss.pending.length - 1; i >= 0; i--) {
          const item = ss.pending[i];
          item.delay -= 1;
          if (item.delay <= 0) {
            S.spawnEnemy(game, item.def);
            ss.pending.splice(i, 1);
          }
        }
        const alive = game.enemies.filter((e) => e.state !== 'defeated' || e.defeatedTicks < 30);
        if (ss.pending.length === 0 && alive.length === 0 && game.tick > (ss.waveStartTick || 0) + 30) {
          ss.waveActive = false;
          ss.clearedWaves += 1;
          ss.waveIndex += 1;
          game.camera.locked = false;
          ss.banner = ss.waveIndex >= st.waves.length ? null : 'CLEAR';
          ss.bannerTicks = 70;
          game.addScore(500);
          FD.sfx('pickup');
        }
      }
      if (!ss.waveActive && ss.waveIndex >= st.waves.length && p.x >= st.finishLineX) {
        ss.finished = true;
        game.onStageClear();
      }
    }

    // ---- cleanup defeated enemies after the fade
    for (let i = game.enemies.length - 1; i >= 0; i--) {
      if (game.enemies[i].state === 'defeated' && game.enemies[i].defeatedTicks > 80) {
        game.enemies.splice(i, 1);
      }
    }

    // ---- camera
    const cam = game.camera;
    if (cam.locked) {
      cam.x = FD.lerp(cam.x, ss.waveLockX, 0.12);
    } else {
      const lookahead = p.facing * 26;
      const target = FD.clamp(p.x - 240 + lookahead, 0, st.worldWidth - FD.VIEW_W);
      cam.x = FD.lerp(cam.x, target, 0.08);
      if (Math.abs(cam.x - target) < 0.4) cam.x = target;
    }
    cam.x = FD.clamp(cam.x, 0, st.worldWidth - FD.VIEW_W);

    // ---- props
    for (const prop of game.props) {
      prop.hitFlash = Math.max(0, prop.hitFlash - 1);
    }

    // ---- pickups
    for (let i = game.pickups.length - 1; i >= 0; i--) {
      const pick = game.pickups[i];
      pick.ttl -= 1;
      pick.bob += 0.08;
      if (pick.ttl <= 0) {
        game.pickups.splice(i, 1);
        continue;
      }
      const dx = Math.abs(pick.x - p.x);
      const dz = Math.abs(pick.z - p.z);
      if (dx < 16 && dz < 12 && !p.dead) {
        game.collectPickup(pick);
        game.pickups.splice(i, 1);
      }
    }
  };

  // Player movement is limited to the visible arena; the camera pushes forward
  // when the player walks into the deadzone.
  S.arena = function (game) {
    const st = FD.cfg.stage;
    const cam = game.camera.x;
    return {
      minX: Math.max(6, cam + 12),
      maxX: Math.min(st.worldWidth - 6, cam + FD.VIEW_W - 12),
      minZ: st.laneMin,
      maxZ: st.laneMax,
    };
  };

  S.hitProp = function (game, prop, damage, dir) {
    if (prop.broken) return;
    prop.hp -= damage;
    prop.hitFlash = 8;
    game.shake = Math.max(game.shake, 1.8);
    game.hitstop = Math.max(game.hitstop, 2);
    FD.sfx('punch', { volume: 0.5, rate: 0.7 });
    game.addEffect({
      type: 'debris', x: prop.x, y: prop.z - prop.h / 2, t: 0, life: 22,
      color: prop.type === 'barrel' ? '#6a7a8c' : prop.type === 'trash' ? '#5a6272' : '#7a5230',
      dir,
    });
    if (prop.hp <= 0) {
      prop.broken = true;
      if (game.stats) game.stats.propsBroken += 1;
      game.shake = Math.max(game.shake, 3.2);
      FD.sfx('break');
      const dropCfg = FD.cfg.stage.pickups[prop.drop];
      if (dropCfg) {
        game.pickups.push({
          type: prop.drop, x: prop.x, z: prop.z, ttl: dropCfg.ttl, bob: Math.random() * 6,
          label: dropCfg.label,
        });
      }
      game.addEffect({ type: 'break', x: prop.x, y: prop.z - prop.h / 2, t: 0, life: 26, dir });
    }
  };

  S.collectPickup = function (game, pick) {
    const def = FD.cfg.stage.pickups[pick.type];
    if (!def) return;
    if (pick.type === 'health') {
      game.player.health = Math.min(game.player.maxHealth, game.player.health + def.heal);
      game.addEffect({ type: 'heal', x: pick.x, y: pick.z - 50, t: 0, life: 34 });
      game.addScore(50);
    } else {
      game.addScore(def.points);
    }
    FD.sfx('pickup');
    game.addEffect({
      type: 'text', x: pick.x, y: pick.z - 64, t: 0, life: 46,
      text: pick.type === 'health' ? `+${def.heal} HP` : `+${def.points}`, color: 'green',
    });
  };

  FD.Stage = S;
})();
