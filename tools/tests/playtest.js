#!/usr/bin/env node
// Scripted end-to-end playtest of stage 1.
// 1. Runs the autopilot through stage 1, recording an event log.
// 2. Saves proof frames for each notable beat.
// 3. Stops as soon as stage 2 starts (the campaign hand-off) so the run stays
//    a single-stage playtest.
// 4. Writes artifacts/playtest.json + artifacts/playtest/*.png
'use strict';
const fs = require('fs');
const path = require('path');
const { loadProject, makeGame, savePng, ROOT } = require('../capture/harness');

const OUT = path.join(ROOT, 'artifacts/playtest');
const LOG = path.join(ROOT, 'artifacts/playtest.json');

(async () => {
  const { FD } = await loadProject();
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(OUT, { recursive: true });
  const game = makeGame(FD, 'stage');
  game.autopilot = true;
  const stageId = FD.cfg.stage.id;

  const events = [];
  const seen = new Set();
  let last = {};
  const snap = (tick, ev, extra = {}) => events.push({ tick, seconds: +(tick / 60).toFixed(2), event: ev, ...extra });

  const captured = [
    { id: 'move', when: () => game.player.state === 'walk', title: 'player walks' },
    { id: 'attack', when: () => game.player.state === 'attack', title: 'player attacks' },
    { id: 'enemy-hit', when: () => game.enemies.some((e) => e.state === 'hurt'), title: 'enemy is hit' },
    { id: 'enemy-attack', when: () => game.enemies.some((e) => e.state === 'attack'), title: 'enemy attacks' },
    { id: 'prop-break', when: () => game.props.some((p) => p.broken), title: 'prop destroyed' },
    { id: 'knockdown', when: () => game.enemies.some((e) => e.state === 'fall' || e.state === 'defeated'), title: 'enemy knocked down' },
    { id: 'special', when: () => game.player.state === 'special', title: 'special move' },
    { id: 'player-hurt', when: () => game.player.state === 'hurt', title: 'player hurt' },
    { id: 'wave2', when: () => game.stageState.waveIndex >= 1, title: 'wave 2 starts' },
    { id: 'wave3', when: () => game.stageState.waveIndex >= 2, title: 'wave 3 starts' },
    { id: 'clear', when: () => game.state === 'stageclear', title: 'stage clear' },
    { id: 'stage2', when: () => game.stageIndex === 1 && game.state === 'intro', title: 'stage 2 intro' },
  ];

  let framesCaptured = 0;
  let ticks = 0;
  const limit = 60 * 200;
  while (ticks < limit && game.stageIndex === 0 && game.state !== 'gameover') {
    game.update();
    ticks++;
    for (const c of captured) {
      if (seen.has(c.id)) continue;
      if (c.when()) {
        seen.add(c.id);
        game.draw();
        const file = `${String(framesCaptured).padStart(2, '0')}-${c.id}.png`;
        savePng(game.canvas, path.join(OUT, file), 3);
        framesCaptured++;
        snap(ticks, c.title, { frame: file, state: game.state, x: Math.round(game.player.x) });
      }
    }
    const st = game.stageState;
    if (last.wave !== st.waveIndex) {
      last.wave = st.waveIndex;
      if (st.waveIndex > 0) snap(ticks, `wave ${st.waveIndex} cleared`);
    }
    const alive = game.enemies.filter((e) => e.state !== 'defeated').length;
    if (alive !== last.alive) {
      if (last.alive !== undefined) snap(ticks, alive > last.alive ? 'enemies spawned' : 'enemy defeated', { alive });
      last.alive = alive;
    }
    if (!game.player.dead && game.player.health <= 0) snap(ticks, 'player died');
  }
  if (game.stageIndex > 0 || game.state === 'results') {
    snap(ticks, 'stage completed');
    game.draw();
    savePng(game.canvas, path.join(OUT, `${String(framesCaptured).padStart(2, '0')}-results.png`), 3);
  }

  const out = {
    generatedAt: new Date().toISOString(),
    stage: stageId,
    endedIn: game.state === 'gameover' ? 'gameover' : 'stage_cleared',
    nextStage: game.stageIndex > 0 ? game.stageIndex + 1 : null,
    ticks,
    seconds: +(ticks / 60).toFixed(2),
    results: game.results,
    stats: game.stats,
    events,
    frames: framesCaptured,
  };
  fs.writeFileSync(LOG, JSON.stringify(out, null, 2) + '\n');
  console.log(`playtest: ${out.endedIn} in ${out.seconds}s, ${events.length} events, ${framesCaptured} proof frames`);
  console.log(`results: ${JSON.stringify(out.results)}, stats ${JSON.stringify(out.stats)}`);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
