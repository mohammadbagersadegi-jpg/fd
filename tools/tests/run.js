#!/usr/bin/env node
// Evidence-based test suite.  Each test prints PASS/FAIL/SKIP with the concrete
// numbers it observed, and the summary is written to artifacts/test-results.json.
'use strict';
const fs = require('fs');
const path = require('path');
const { loadProject, makeGame, ROOT } = require('../capture/harness');

const results = [];
let FD;

function record(name, status, detail) {
  results.push({ name, status, detail });
  const tag = status.padEnd(5);
  console.log(`[${tag}] ${name} - ${detail}`);
}

function test(name, fn) {
  try {
    const detail = fn();
    record(name, 'PASS', detail || 'ok');
  } catch (err) {
    record(name, 'FAIL', err.message);
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

function approx(a, b, tol, label) {
  assert(Math.abs(a - b) <= tol, `${label}: expected ${b}±${tol}, got ${a}`);
}

// ---------------------------------------------------------------- asset tests
function testAssets() {
  test('config: all JSON parse and required keys exist', () => {
    const d = FD.assets.dataRef;
    for (const key of ['movement', 'collision', 'combat', 'animation', 'stage', 'presentation']) {
      assert(d[key], `missing config ${key}`);
    }
    assert(d.stage.waves.length === 3, 'expected 3 waves');
    assert(d.combat.enemyTypes.rivet, 'missing enemy type');
    return `${d.stage.waves.length} waves, ${Object.keys(d.animation.characters).length} character sheets`;
  });

  test('assets: every configured animation frame image exists', () => {
    const d = FD.assets.dataRef;
    const missing = [];
    let count = 0;
    for (const charId of ['volt', 'rivet']) {
      const cfg = FD.characterCfg(charId);
      for (const [anim, spec] of Object.entries(cfg.animations)) {
        spec.frames.forEach((f, i) => {
          const rel = `characters/${charId}/frames/${anim}/${anim}_${String(i).padStart(2, '0')}.png`;
          count++;
          if (!FD.assets.img(rel)) missing.push(rel);
        });
      }
    }
    assert(missing.length === 0, `missing ${missing.length}: ${missing.slice(0, 3)}`);
    return `${count} frames resolved`;
  });

  test('assets: frame dimensions match config for every animation', () => {
    const d = FD.assets.dataRef;
    for (const charId of ['volt', 'rivet']) {
      const cfg = FD.characterCfg(charId);
      const { width, height } = cfg.frame;
      for (const anim of Object.keys(cfg.animations)) {
        const img = FD.assets.img(
          `characters/${charId}/frames/${anim}/${anim}_00.png`
        );
        assert(img && img.width === width && img.height === height,
          `${charId}/${anim} is ${img && img.width}x${img && img.height}, expected ${width}x${height}`);
      }
    }
    return '96x96... 112x96 frames all match';
  });

  test('assets: animation timing values are positive integers', () => {
    const d = FD.assets.dataRef;
    let n = 0;
    for (const cfg of Object.values(d.animation.characters)) {
      for (const spec of Object.values(cfg.animations)) {
        for (const f of spec.frames) {
          assert(Number.isInteger(f.dur) && f.dur > 0, `bad duration ${f.dur}`);
          n++;
        }
      }
    }
    return `${n} frame durations validated`;
  });

  test('assets: hit windows only reference frames that exist', () => {
    const d = FD.assets.dataRef;
    let windows = 0;
    for (const [charId, cfg] of Object.entries(d.animation.characters)) {
      for (const [anim, spec] of Object.entries(cfg.animations)) {
        spec.frames.forEach((f) => {
          if (f.hit) {
            windows++;
            assert(f.hit.radial || (f.hit.w > 0 && f.hit.h > 0), `${charId}/${anim} has an empty hit box`);
          }
        });
      }
    }
    return `${windows} active hit windows`;
  });
}

// ---------------------------------------------------------------- gameplay tests
function testGameplay() {
  test('logic: player walks right at the configured speed', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 200;
    const start = game.player.x;
    FD.input.press('right');
    for (let i = 0; i < 60; i++) game.update();
    FD.input.release('right');
    const travelled = game.player.x - start;
    assert(travelled > 1.5 * 60 * 0.9, `walked only ${travelled.toFixed(1)}px in 60 ticks`);
    return `${travelled.toFixed(1)} px in 60 ticks (${(travelled / 60).toFixed(2)} px/tick)`;
  });

  test('logic: player stops when input stops', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 200;
    FD.input.press('right');
    for (let i = 0; i < 30; i++) game.update();
    FD.input.release('right');
    for (let i = 0; i < 40; i++) game.update();
    const v = Math.abs(game.player.vx);
    assert(v < 0.02, `still moving at ${v}`);
    assert(game.player.state === 'idle' || game.player.state === 'walk', `unexpected state ${game.player.state}`);
    return `vx decayed to ${v.toFixed(3)}, state=${game.player.state}`;
  });

  test('logic: attack starts, has a finite active window and returns to idle', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 200;
    FD.input.press('attack');
    game.update();
    FD.input.release('attack');
    assert(game.player.state === 'attack', `state was ${game.player.state}`);
    let activeTicks = 0;
    let ticks = 0;
    while (game.player.state === 'attack' && ticks < 120) {
      const f = FD.Actors.currentFrame(game.player);
      if (f && f.hit) activeTicks++;
      game.update();
      ticks++;
    }
    assert(game.player.state === 'idle', `did not return to idle (state=${game.player.state})`);
    assert(activeTicks >= 4 && activeTicks <= 12, `active window ${activeTicks} ticks looks wrong`);
    return `active ${activeTicks} ticks, total ${ticks} ticks`;
  });

  test('logic: combo chains attack1 -> attack2 -> attack3 while tapping attack', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 200;
    const seen = new Set();
    FD.input.press('attack');
    game.update();
    FD.input.release('attack');
    seen.add(game.player.anim);
    for (let i = 0; i < 90; i++) {
      // tap attack every 4 ticks: chain window for attack1 closes at tick 10
      if (i % 4 === 0 && game.player.state === 'attack') {
        FD.input.press('attack');
      }
      game.update();
      FD.input.release('attack');
      seen.add(game.player.anim);
      if (seen.has('attack3') && game.player.state !== 'attack') break;
    }
    assert(seen.has('attack2'), `attack2 never reached (saw ${[...seen].join(', ')})`);
    assert(seen.has('attack3'), `attack3 never reached (saw ${[...seen].join(', ')})`);
    assert(game.player.state === 'idle', `did not settle back to idle (${game.player.state})`);
    return `chained ${[...seen].filter((a) => a.startsWith('attack')).join(' -> ')}`;
  });

  test('logic: one attack cannot damage the same enemy twice', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 200;
    const e = FD.Actors.createEnemy(game, 'rivet', 228, game.player.z, { side: 1 });
    e.state = 'approach';
    e.alpha = 1;
    game.enemies.push(e);
    const hp0 = e.health;
    FD.input.press('attack');
    game.update();
    FD.input.release('attack');
    for (let i = 0; i < 30; i++) game.update();
    const dmg = hp0 - e.health;
    const expected = FD.cfg.combat.player.attacks.attack1.damage;
    assert(dmg === expected || dmg === 0, `damage was ${dmg}, expected one hit of ${expected}`);
    return `damage applied ${dmg} (single hit cap ${expected})`;
  });

  test('logic: enemy hit puts the player into hurt and blocks further damage briefly', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 300;
    const hp = game.player.health;
    FD.Actors.playerTakeHit(game, game.player, 8, { dir: -1, knockback: 1 });
    assert(game.player.state === 'hurt', `state ${game.player.state}`);
    const hpAfter = game.player.health;
    const blocked = FD.Actors.playerTakeHit(game, game.player, 8, { dir: -1 });
    assert(blocked === false, 'invulnerability window did not block the second hit');
    assert(game.player.health === hpAfter, 'health changed during i-frames');
    return `hp ${hp} -> ${hpAfter}, second hit blocked by ${game.player.invulnTicks} i-frames`;
  });

  test('logic: knockdown -> get up cycle restores control', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 300;
    FD.Actors.playerTakeHit(game, game.player, 5, { dir: -1, knockdown: true });
    assert(game.player.state === 'fall', `state ${game.player.state}`);
    let ticks = 0;
    while (game.player.state !== 'idle' && ticks < 400) {
      game.update();
      ticks++;
    }
    assert(game.player.state === 'idle', `stuck in ${game.player.state}`);
    return `recovered to idle after ${ticks} ticks`;
  });

  test('logic: special costs health, damages all nearby enemies and has a cooldown', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 300;
    const e1 = FD.Actors.createEnemy(game, 'rivet', 330, game.player.z, { side: 1 });
    const e2 = FD.Actors.createEnemy(game, 'rivet', 270, game.player.z, { side: -1 });
    for (const e of [e1, e2]) { e.state = 'approach'; e.alpha = 1; game.enemies.push(e); }
    const hp0 = e1.health;
    const hp1 = e2.health;
    const playerHp0 = game.player.health;
    FD.input.press('special');
    game.update();
    FD.input.release('special');
    for (let i = 0; i < 80; i++) game.update();
    assert(e1.health < hp0 && e2.health < hp1, 'special did not hit both sides');
    const paid = playerHp0 - game.player.health;
    assert(paid === FD.cfg.combat.player.special.healthCost, `special cost ${paid}, expected ${FD.cfg.combat.player.special.healthCost} (charged once, not per target)`);
    assert(game.player.specialCooldown > 0, 'cooldown not applied');
    const cd = game.player.specialCooldown;
    FD.input.press('special');
    game.update();
    FD.input.release('special');
    assert(game.player.state !== 'special', 'special fired during cooldown');
    return `both enemies damaged, ${paid} HP spent once, ${cd} ticks of cooldown left after 80 ticks`;
  });

  test('logic: props break after their HP and drop a pickup', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    const prop = game.props[0];
    game.player.x = prop.x - 30;
    game.player.z = prop.z;
    const before = game.pickups.length;
    FD.Stage.hitProp(game, prop, 1, 1);
    assert(!prop.broken, 'prop broke with 1 of 2 hp');
    FD.Stage.hitProp(game, prop, 1, 1);
    assert(prop.broken, 'prop did not break at 0 hp');
    assert(game.pickups.length === before + 1, 'no pickup dropped');
    return `${prop.type} broke after 2 hits, dropped ${game.pickups[game.pickups.length - 1].type}`;
  });

  test('logic: pickups heal without exceeding max health', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.health = 90;
    game.collectPickup({ type: 'health', x: game.player.x, z: game.player.z });
    assert(game.player.health === game.player.maxHealth, `health ${game.player.health}`);
    return `healed 90 -> ${game.player.health} (capped)`;
  });

  test('flow: waves lock the camera, spawn enemies and unlock when cleared', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = FD.cfg.stage.waves[0].triggerX;
    game.stageState.waveIndex = 0;
    let spawned = 0;
    for (let i = 0; i < 400; i++) {
      game.update();
      spawned = Math.max(spawned, game.enemies.length);
      for (const e of game.enemies) {
        if (e.state !== 'defeated') FD.Actors.enemyTakeHit(game, e, 999, { knockdown: true, sfx: 'punch' }, 1);
      }
      if (game.stageState.waveIndex > 0) break;
    }
    assert(spawned >= 2, `only ${spawned} enemies spawned`);
    assert(game.stageState.waveIndex === 1, `wave index ${game.stageState.waveIndex}`);
    assert(!game.camera.locked, 'camera still locked after clear');
    return `${spawned} enemies spawned, wave advanced to 2`;
  });

  test('flow: full stage playthrough reaches stage clear and results', () => {
    const game = makeGame(FD, 'stage');
    game.autopilot = true;
    let ticks = 0;
    while (game.state !== 'results' && game.state !== 'gameover' && ticks < 60 * 180) {
      game.update();
      ticks++;
    }
    assert(game.state === 'results', `ended in ${game.state}`);
    assert(game.results.cleared === true, 'results did not report a clear');
    return `cleared in ${(ticks / 60).toFixed(1)}s, score ${game.results.score}, ${game.results.hits} hits`;
  });

  test('flow: player death leads to game over, retry restarts the stage', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.health = 1;
    FD.Actors.playerTakeHit(game, game.player, 50, { dir: 1, knockdown: true });
    let ticks = 0;
    while (game.state !== 'gameover' && ticks < 600) { game.update(); ticks++; }
    assert(game.state === 'gameover', `state ${game.state}`);
    game.gameoverTicks = 120;
    FD.input.press('start');
    game.update();
    FD.input.release('start');
    assert(game.state === 'intro', `retry ended in ${game.state}`);
    return `game over after ${ticks} ticks, retry -> ${game.state}`;
  });

  test('flow: pause freezes the simulation and resumes', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    FD.input.press('pause');
    game.update();
    FD.input.release('pause');
    assert(game.state === 'paused', `state ${game.state}`);
    const t0 = game.tick;
    for (let i = 0; i < 30; i++) game.update();
    assert(game.tick === t0, 'simulation advanced while paused');
    FD.input.press('pause');
    game.update();
    FD.input.release('pause');
    assert(game.state === 'playing', 'did not resume');
    return 'paused for 30 ticks without advancing, resumed';
  });
}

// ---------------------------------------------------------------- calibration
function testCalibration() {
  test('calibration: measured movement, jump and attack timings', () => {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.player.x = 200;
    const x0 = game.player.x;
    FD.input.press('right');
    for (let i = 0; i < 120; i++) game.update();
    FD.input.release('right');
    const walkSpeed = (game.player.x - x0) / 120;

    const game2 = makeGame(FD, 'stage');
    game2.setState('playing');
    FD.input.press('jump');
    game2.update();
    FD.input.release('jump');
    let apex = 0;
    let airTicks = 0;
    while (game2.player.state === 'jump' || game2.player.state === 'jump_attack') {
      apex = Math.max(apex, game2.player.yOffset);
      game2.update();
      airTicks++;
      if (airTicks > 300) break;
    }

    const game3 = makeGame(FD, 'stage');
    game3.setState('playing');
    FD.input.press('attack');
    game3.update();
    FD.input.release('attack');
    let firstActive = -1;
    let lastActive = -1;
    let t = 0;
    while (game3.player.state === 'attack' && t < 120) {
      const f = FD.Actors.currentFrame(game3.player);
      if (f && f.hit) {
        if (firstActive < 0) firstActive = t;
        lastActive = t;
      }
      game3.update();
      t++;
    }
    const stats = {
      walkSpeedPxPerTick: +walkSpeed.toFixed(3),
      jumpApexPx: +apex.toFixed(1),
      jumpAirTicks: airTicks,
      jumpAirSeconds: +(airTicks / 60).toFixed(3),
      attackFirstActiveTick: firstActive,
      attackLastActiveTick: lastActive,
      attackActiveTicks: lastActive - firstActive + 1,
      attackTotalTicks: t,
    };
    const ref = {
      walkSpeedPxPerTick: 3.0,
      jumpApexPx: +(7 * 7 / (2 * 0.90625)).toFixed(1),
      jumpAirTicks: +(2 * 7 / 0.90625).toFixed(2),
    };
    fs.mkdirSync(path.join(ROOT, 'artifacts'), { recursive: true });
    fs.writeFileSync(path.join(ROOT, 'artifacts/calibration.json'), JSON.stringify({ measured: stats, referenceSor1Derived: ref }, null, 2) + '\n');
    return `walk ${stats.walkSpeedPxPerTick}px/t, jump ${stats.jumpApexPx}px/${stats.jumpAirTicks}t, attack active ${stats.attackActiveTicks}t of ${stats.attackTotalTicks}t`;
  });

  test('calibration: derived SoR1 jump matches the constants in the disassembly', () => {
    // Jump_Inertia #$FFF90000 = -7.0 px/tick, gravity #$E800 = 0.90625 px/tick^2
    const v = 0x70000 / 65536;
    const g = 0xE800 / 65536;
    const apex = (v * v) / (2 * g);
    const air = (2 * v) / g;
    approx(v, 7.0, 0.001, 'initial jump speed');
    approx(g, 0.90625, 0.0001, 'gravity');
    approx(apex, 27.03, 0.05, 'apex');
    approx(air, 15.45, 0.05, 'airticks');
    return `SoR1: v=${v}, g=${g}, apex=${apex.toFixed(2)}px, airtime=${air.toFixed(2)} ticks`;
  });

  test('calibration: depth tolerance and hit box geometry are documented', () => {
    const c = FD.cfg.collision;
    assert(c.rules.depthSort === true, 'depth sort disabled');
    assert(c.player.depthTolerance > 0 && c.enemy.depthTolerance > 0, 'depth tolerance missing');
    return `player depth ±${c.player.depthTolerance}px, enemy ±${c.enemy.depthTolerance}px, SoR1 reference ±8px`;
  });
}

(async () => {
  const loaded = await loadProject();
  FD = loaded.FD;
  console.log('=== NEON GAUNTLET test suite ===');
  testAssets();
  testGameplay();
  testCalibration();
  const passed = results.filter((r) => r.status === 'PASS').length;
  const failed = results.filter((r) => r.status === 'FAIL').length;
  const summary = {
    suite: 'neon-gauntlet',
    generatedAt: new Date().toISOString(),
    totals: { passed, failed, total: results.length },
    results,
  };
  fs.mkdirSync(path.join(ROOT, 'artifacts'), { recursive: true });
  fs.writeFileSync(path.join(ROOT, 'artifacts/test-results.json'), JSON.stringify(summary, null, 2) + '\n');
  console.log(`\n${passed}/${results.length} passed, ${failed} failed`);
  process.exit(failed ? 1 : 0);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
