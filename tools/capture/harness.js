// Headless runtime for the game: provides just enough DOM/canvas surface for
// the browser modules to run under Node with @napi-rs/canvas.
'use strict';
const fs = require('fs');
const path = require('path');
const napi = require('@napi-rs/canvas');

const ROOT = path.resolve(__dirname, '../..');
const GAME = path.join(ROOT, 'game');
const ASSETS = path.join(GAME, 'assets');

function makeDocument() {
  return {
    createElement(tag) {
      if (tag === 'canvas') return napi.createCanvas(1, 1);
      return { style: {}, classList: { add() {}, remove() {} }, appendChild() {} };
    },
    getElementById() { return null; },
    addEventListener() {},
    body: { appendChild() {} },
  };
}

async function loadImageCanvas(file) {
  const img = await napi.loadImage(file);
  const cv = napi.createCanvas(img.width, img.height);
  cv.getContext('2d').drawImage(img, 0, 0);
  return cv;
}

async function loadProject() {
  global.window = global;
  global.document = makeDocument();
  global.requestAnimationFrame = () => 0;
  global.performance = global.performance || { now: () => Date.now() };
  if (!global.navigator) {
    Object.defineProperty(global, 'navigator', { value: { getGamepads: () => [] }, configurable: true });
  }
  global.localStorage = { getItem: () => null, setItem: () => {} };
  global.addEventListener = () => {};
  global.Image = class {
    set src(_v) { /* images are preloaded by the harness */ }
  };

  const files = [
    'src/generated/data.js',
    '../game/assets/fonts/font5x7.js',
    'src/core.js', 'src/assets.js', 'src/font.js', 'src/input.js', 'src/audio.js',
    'src/actors.js', 'src/stage.js', 'src/render.js', 'src/cinematic.js', 'src/main.js',
  ];
  for (const rel of files) {
    const code = fs.readFileSync(path.join(GAME, rel), 'utf8');
    // eslint-disable-next-line no-eval
    (0, eval)(code);
  }

  const FD = global.FD;
  FD.assets.dataRef = global.FD_DATA;
  FD.assets.fontRef = global.FD_FONT;
  const images = Object.create(null);
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith('.png')) {
        const rel = path.relative(ASSETS, full).split(path.sep).join('/');
        images[rel] = full;
      }
    }
  };
  walk(ASSETS);
  for (const [rel, file] of Object.entries(images)) {
    FD.assets.images[rel] = await loadImageCanvas(file);
  }
  FD.assets.ready = true;
  FD.assets.filmMode = true;
  return { FD, ROOT, GAME, ASSETS };
}

function makeGame(FD, state = 'title') {
  const canvas = napi.createCanvas(FD.VIEW_W, FD.VIEW_H);
  const game = FD.createGame(canvas);
  FD.font.atlas('white');
  game.startTitle();
  if (state === 'stage') game.startStage();
  return game;
}

function savePng(canvas, file, scale = 2) {
  const out = napi.createCanvas(canvas.width * scale, canvas.height * scale);
  const ctx = out.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(canvas, 0, 0, out.width, out.height);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, out.toBuffer('image/png'));
}

module.exports = { loadProject, makeGame, savePng, ROOT, GAME, ASSETS };
