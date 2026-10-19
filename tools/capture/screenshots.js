#!/usr/bin/env node
// Render a set of verification screenshots headlessly (no browser needed).
'use strict';
const fs = require('fs');
const path = require('path');
const { loadProject, makeGame, savePng, ROOT } = require('./harness');

const OUT = path.join(ROOT, 'artifacts/screenshots');

(async () => {
  const { FD } = await loadProject();
  fs.mkdirSync(OUT, { recursive: true });
  const shots = [];

  function shot(name, game) {
    game.draw();
    savePng(game.canvas, path.join(OUT, `${name}.png`), 3);
    shots.push(name);
  }

  // title
  {
    const game = makeGame(FD, 'title');
    game.step(40);
    shot('01-title', game);
  }
  // cinematic key frames
  {
    const game = makeGame(FD, 'stage');
    game.setState('cinematic');
    for (const t of [0.8, 2.0, 4.6, 7.6, 10.4]) {
      game.cinematicT = t;
      game.draw();
      savePng(game.canvas, path.join(OUT, `02-cinematic-${t.toFixed(1)}s.png`), 3);
      shots.push(`cinematic-${t}`);
    }
  }
  // stage intro
  {
    const game = makeGame(FD, 'stage');
    game.step(80);
    shot('03-stage-intro', game);
  }
  // gameplay: waves, combat, special, props, clear
  {
    const game = makeGame(FD, 'stage');
    game.autopilot = true;
    let shotWave = false;
    let shotSpecial = false;
    let shotProp = false;
    let shotHurt = false;
    for (let i = 0; i < 60 * 60 * 20; i++) {
      if (!shotHurt && i === 480 && game.state === 'playing') {
        // Deterministic hurt pose: the autopilot may never get hit on a lucky
        // run, so force one clean hit for the screenshot.
        FD.Actors.playerTakeHit(game, game.player, 8, { dir: -1, knockback: 1.4 });
      }
      game.update();
      if (game.state === 'results' || game.state === 'gameover') break;
      if (game.state !== 'playing') continue;
      if (!shotWave && game.enemies.some((e) => e.state === 'attack')) {
        game.draw(); savePng(game.canvas, path.join(OUT, '04-combat.png'), 3); shotWave = true; shots.push('combat');
      }
      if (!shotSpecial && game.player.state === 'special') {
        game.draw(); savePng(game.canvas, path.join(OUT, '05-special.png'), 3); shotSpecial = true; shots.push('special');
      }
      if (!shotProp && game.props.some((p) => p.broken)) {
        game.draw(); savePng(game.canvas, path.join(OUT, '06-prop-break.png'), 3); shotProp = true; shots.push('prop');
      }
      if (!shotHurt && game.player.state === 'hurt') {
        game.draw(); savePng(game.canvas, path.join(OUT, '07-player-hurt.png'), 3); shotHurt = true; shots.push('hurt');
      }
      if (shotHurt && !game.debug.invincible) {
        // All action shots are in the can; invincibility lets the run finish
        // the whole campaign so the results screen is the real one.
        game.debug.invincible = true;
      }
    }
    if (game.state !== 'results') {
      // retry with invincibility from the top: progression, not survival
      const g2 = makeGame(FD, 'stage');
      g2.autopilot = true;
      g2.debug.invincible = true;
      for (let i = 0; i < 60 * 60 * 20 && g2.state !== 'results'; i++) g2.update();
      shot('09-results', g2);
    } else {
      shot('09-results', game);
    }
    console.log(`  autopilot ended in ${game.state} after ${(game.tick / 60).toFixed(1)}s`);
  }
  // stage 1 clear banner (separate run, captured before the hand-off)
  {
    const game = makeGame(FD, 'stage');
    game.autopilot = true;
    game.debug.invincible = true;
    for (let i = 0; i < 60 * 120 && game.state !== 'stageclear'; i++) game.update();
    if (game.state !== 'stageclear') throw new Error(`stage 1 did not clear (${game.state})`);
    game.step(40);
    shot('08-stage-clear', game);
  }
  // game over
  {
    const game = makeGame(FD, 'stage');
    game.setState('playing');
    game.stageState.banner = null;
    game.player.health = 1;
    game.timerTicks = 2;
    game.step(200);
    shot('10-game-over', game);
  }
  console.log(`wrote ${shots.length} screenshots to artifacts/screenshots/`);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
