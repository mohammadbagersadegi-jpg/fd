#!/usr/bin/env node
// Deterministic offline renderer for the intro cinematic and the gameplay reel.
// Canvas frames are streamed into ffmpeg (bundled with imageio-ffmpeg).
'use strict';
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { loadProject, makeGame, ROOT } = require('./harness');

const OUT = path.join(ROOT, 'artifacts/video');
const FPS = 30;
const SCALE = 3; // 480x270 -> 1440x810

function ffmpegPath() {
  if (process.env.FFMPEG) return process.env.FFMPEG;
  const venv = path.join(ROOT, '.venv/bin/python');
  const candidates = [
    path.join(process.env.HOME || '/root', '.local/bin/python3'),
    '/tmp/venv/bin/python',
    '/usr/bin/python3',
  ];
  for (const py of candidates) {
    try {
      const out = require('child_process').execFileSync(py, ['-c', 'import imageio_ffmpeg,sys;sys.stdout.write(imageio_ffmpeg.get_ffmpeg_exe())'], { encoding: 'utf8' });
      if (out && fs.existsSync(out)) return out;
    } catch (e) { /* try next */ }
  }
  throw new Error('ffmpeg not found: set FFMPEG=/path/to/ffmpeg or pip install imageio-ffmpeg');
}

function startEncoder(file, audioFile) {
  const ff = ffmpegPath();
  const args = [
    '-y', '-hide_banner', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  ];
  if (audioFile) args.push('-i', audioFile);
  args.push(
    '-vf', `scale=${480 * SCALE}:${270 * SCALE}:flags=neighbor`,
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart'
  );
  if (audioFile) args.push('-c:a', 'aac', '-b:a', '192k', '-shortest');
  args.push(file);
  const proc = spawn(ff, args, { stdio: ['pipe', 'inherit', 'inherit'] });
  return proc;
}

async function renderCinematic(FD, file) {
  const game = makeGame(FD, 'stage');
  game.setState('cinematic');
  const total = Math.round(FD.Cinematic.duration * FPS);
  const proc = startEncoder(file);
  for (let i = 0; i < total; i++) {
    const t = i / FPS;
    game.cinematicT = t;
    game.draw();
    const buf = game.canvas.toBuffer('image/png');
    if (!proc.stdin.write(buf)) {
      await new Promise((r) => proc.stdin.once('drain', r));
    }
    if (i % 30 === 0) process.stdout.write(`\rcinematic ${i}/${total}`);
  }
  proc.stdin.end();
  await new Promise((resolve, reject) => {
    proc.on('close', (code) => (code === 0 ? resolve() : reject(new Error('ffmpeg exited ' + code))));
  });
  process.stdout.write(`\rcinematic ${total}/${total} -> ${path.basename(file)}\n`);
  return total / FPS;
}

// Records a full autopilot playthrough at 30fps, sampling the 60Hz simulation
// two ticks per output frame so motion stays faithful.
async function renderGameplay(FD, file, { maxSeconds = 130, startAtIntro = true } = {}) {
  const game = makeGame(FD, 'stage');
  game.autopilot = true;
  const proc = startEncoder(file);
  const totalFrames = maxSeconds * FPS;
  let frames = 0;
  for (let f = 0; f < totalFrames; f++) {
    game.update();
    game.update();
    game.draw();
    const buf = game.canvas.toBuffer('image/png');
    if (!proc.stdin.write(buf)) {
      await new Promise((r) => proc.stdin.once('drain', r));
    }
    frames++;
    if (f % 60 === 0) process.stdout.write(`\rgameplay ${(f / FPS).toFixed(1)}s state=${game.state}`);
    if (game.state === 'results') {
      // hold the results screen for a moment
      for (let k = 0; k < FPS * 3; k++) {
        game.update();
        game.draw();
        const b2 = game.canvas.toBuffer('image/png');
        if (!proc.stdin.write(b2)) await new Promise((r) => proc.stdin.once('drain', r));
        frames++;
      }
      break;
    }
  }
  proc.stdin.end();
  await new Promise((resolve, reject) => {
    proc.on('close', (code) => (code === 0 ? resolve() : reject(new Error('ffmpeg exited ' + code))));
  });
  process.stdout.write(`\rgameplay ${frames} frames -> ${path.basename(file)}\n`);
  return frames / FPS;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const { FD } = await loadProject();
  const which = process.argv[2] || 'all';
  const manifest = { fps: FPS, scale: SCALE, files: {} };
  if (which === 'all' || which === 'cinematic') {
    const dur = await renderCinematic(FD, path.join(OUT, 'cinematic.mp4'));
    manifest.files.cinematic = { file: 'cinematic.mp4', seconds: dur };
  }
  if (which === 'all' || which === 'gameplay') {
    const dur = await renderGameplay(FD, path.join(OUT, 'gameplay.mp4'));
    manifest.files.gameplay = { file: 'gameplay.mp4', seconds: dur };
  }
  const manifestPath = path.join(OUT, 'render-manifest.json');
  let prev = {};
  if (fs.existsSync(manifestPath)) {
    try { prev = JSON.parse(fs.readFileSync(manifestPath, 'utf8')).files || {}; } catch (e) { prev = {}; }
  }
  manifest.files = Object.assign(prev, manifest.files);
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
  console.log('done:', JSON.stringify(manifest.files));
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
