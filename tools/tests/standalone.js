#!/usr/bin/env node
// Verifies the single-file build the way a player would use it:
// no server, no preloaded images - the scripts inside dist/neon-gauntlet.html
// run on their own and decode every PNG from its embedded data URI.
'use strict';
const fs = require('fs');
const path = require('path');
const napi = require('@napi-rs/canvas');
const { ROOT, savePng } = require('../capture/harness');

const HTML = path.join(ROOT, 'dist/neon-gauntlet.html');
const REPORT = path.join(ROOT, 'artifacts/standalone-test.json');

function installDomShim() {
  global.window = global;
  global.location = { search: '', href: 'file:///neon-gauntlet.html' };
  const screen = napi.createCanvas(480, 270);
  const stub = () => ({
    textContent: '',
    style: {},
    classList: { add() {}, remove() {} },
    querySelectorAll: () => [],
    addEventListener() {},
    removeEventListener() {},
    appendChild() {},
  });
  global.document = {
    getElementById(id) {
      if (id === 'screen') return screen;
      return stub();
    },
    createElement(tag) {
      if (tag === 'canvas') return napi.createCanvas(1, 1);
      return stub();
    },
    addEventListener() {},
    body: { appendChild() {} },
  };
  global.Image = napi.Image; // real PNG decode from a data URI, like a browser
  global.requestAnimationFrame = () => 0;
  global.cancelAnimationFrame = () => {};
  global.performance = global.performance || { now: () => Date.now() };
  global.localStorage = { getItem: () => null, setItem: () => {} };
  global.addEventListener = () => {};
  global.removeEventListener = () => {};
  if (!global.navigator) {
    Object.defineProperty(global, 'navigator', {
      value: { getGamepads: () => [] },
      configurable: true,
    });
  }
  return screen;
}

function extractScripts(html) {
  const out = [];
  const re = /<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi;
  let m;
  while ((m = re.exec(html))) out.push(m[1]);
  return out;
}

(async () => {
  if (!fs.existsSync(HTML)) {
    console.error(`missing ${path.relative(ROOT, HTML)} - run tools/build_standalone.py first`);
    process.exit(1);
  }
  const html = fs.readFileSync(HTML, 'utf8');
  const external = [...html.matchAll(/<(?:script|link|img)[^>]+(?:src|href)="(?!#|data:)([^"]+)"/gi)];
  if (external.length) throw new Error(`build still references ${external[0][1]}`);

  installDomShim();
  const scripts = extractScripts(html);
  for (const code of scripts) (0, eval)(code);

  if (!global.FD || !FD.assets) throw new Error('the page did not boot the FD namespace');
  if (!window.FD_EMBED) throw new Error('FD_EMBED is missing from the build');

  const game = await FD.boot({ autostart: false });
  const loaded = Object.keys(FD.assets.images).length;
  if (FD.assets.failures.length) {
    throw new Error(`embedded images failed to decode: ${FD.assets.failures.slice(0, 3).join(', ')}`);
  }
  if (loaded < 100) throw new Error(`only ${loaded} images decoded`);

  game.autopilot = true;
  game.startStage();
  game.setState('intro');
  let ticks = 0;
  while (!['results', 'gameover'].includes(game.state) && ticks < 60 * 180) {
    game.update();
    ticks++;
    if (ticks % 8 === 0) game.draw();
  }
  game.draw();
  savePng(game.canvas, path.join(ROOT, 'artifacts/standalone-proof.png'), 2);

  const ok = game.state === 'results' && game.results && game.results.cleared;
  const report = {
    file: 'dist/neon-gauntlet.html',
    bytes: fs.statSync(HTML).size,
    scriptsInlined: scripts.length,
    imagesEmbedded: window.FD_EMBED ? Object.keys(window.FD_EMBED.assets).length : 0,
    imagesDecoded: loaded,
    decodeFailures: FD.assets.failures.length,
    endedIn: game.state,
    seconds: +(ticks / 60).toFixed(2),
    score: game.results ? game.results.score : null,
    hits: game.results ? game.results.hits : null,
    cleared: game.state === 'results' && game.results.cleared === true,
    verifiedAt: new Date().toISOString(),
  };
  fs.writeFileSync(REPORT, JSON.stringify(report, null, 2) + '\n');
  console.log(
    `standalone: ${report.imagesDecoded} images from data URIs, 0 external refs, ` +
      `stage ${ok ? 'CLEARED' : 'FAILED'} in ${report.seconds}s (score ${report.score})`
  );
  if (!ok) process.exit(1);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
