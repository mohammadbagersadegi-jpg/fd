// Game shell: fixed-timestep loop, scene flow and the autopilot used for
// recorded footage.  The same class runs in the browser and in the Node
// capture harness (which drives step()/draw() directly).
(function () {
  'use strict';
  const FD = window.FD;

  class Game {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.width = FD.VIEW_W;
      this.height = FD.VIEW_H;
      this.state = 'boot';
      this.tick = 0;
      this.stateTicks = 0;
      this.score = 0;
      this.shake = 0;
      this.hitstop = 0;
      this.effects = [];
      this.ipan = 0;
      this.enemies = [];
      this.props = [];
      this.pickups = [];
      this.player = null;
      this.camera = { x: 0, locked: false };
      this.combo = { count: 0, timer: 0, playerHits: 0 };
      this.stats = { hits: 0, damageTaken: 0, enemiesDefeated: 0, propsBroken: 0 };
      this.debug = { invincible: false, showHitboxes: false };
      this.stageState = null;
      this.timerTicks = 99 * 60;
      this.autopilot = false;
      this.autopilotPlan = { attackCooldown: 0, specialCooldown: 0, dirHold: 0, dir: 0 };
      this.gameoverTicks = 0;
      this.cinematicT = 0;
      this.results = null;
      this.running = false;
      this.acc = 0;
      this.lastTime = 0;
      this.onStateChange = null;
      this.audioKick = false;
    }

    setState(next) {
      const prev = this.state;
      this.state = next;
      this.stateTicks = 0;
      if (this.onStateChange) this.onStateChange(next, prev);
    }

    addScore(n) {
      this.score += n;
    }

    addEffect(fx) {
      fx.t = 0;
      this.effects.push(fx);
      if (this.effects.length > 240) this.effects.shift();
    }

    arena() {
      return FD.Stage.arena(this);
    }

    enemyArena() {
      const st = FD.cfg.stage;
      return {
        minX: Math.max(-40, this.camera.x - 80),
        maxX: Math.min(st.worldWidth + 40, this.camera.x + FD.VIEW_W + 80),
        minZ: st.laneMin,
        maxZ: st.laneMax,
      };
    }

    hitProp(prop, damage, dir) {
      FD.Stage.hitProp(this, prop, damage, dir);
    }

    collectPickup(pick) {
      FD.Stage.collectPickup(this, pick);
    }

    onPlayerLandedHit(def, enemy, isSpecial) {
      this.stats.hits += 1;
      this.combo.count += 1;
      this.combo.timer = 90;
      if (isSpecial) {
        this.shake = Math.max(this.shake, 4.5);
        for (const e of this.enemies) {
          if (Math.abs(e.x - this.player.x) < 90 && e.state !== 'defeated') {
            this.addEffect({ type: 'hit', x: e.x, y: e.z - 40, t: 0, life: 12, color: '#9ff6ff', dir: 1 });
          }
        }
      }
      this.player.flash = 0;
    }

    onPlayerDead() {
      this.gameoverTicks = 0;
    }

    onStageClear() {
      this.player.state = 'victory';
      FD.Actors.setAnim(this.player, 'victory');
      this.results = {
        score: this.score,
        timeLeft: Math.max(0, Math.ceil(this.timerTicks / 60)),
        hits: this.stats.hits,
        damageTaken: this.stats.damageTaken,
        cleared: true,
      };
      this.addEffect({ type: 'ko', x: this.player.x, y: this.player.z - 90, t: 0, life: 60 });
      this.setState('stageclear');
      FD.audio.duckMusic(false);
    }

    startStage() {
      FD.Stage.init(this);
      FD.Renderer.init(this);
      this.setState('intro');
      FD.audio.duckMusic(true);
    }

    startTitle() {
      FD.Stage.init(this);
      FD.Renderer.init(this);
      this.state = 'title';
      this.stateTicks = 0;
      this.score = 0;
      this.timerTicks = 99 * 60;
      this.combo = { count: 0, timer: 0, playerHits: 0 };
      this.stats = { hits: 0, damageTaken: 0, enemiesDefeated: 0, propsBroken: 0 };
      FD.audio.duckMusic(false);
    }

    // ---------------------------------------------------------------- update
    update() {
      this.stateTicks += 1;
      const input = FD.input;

      switch (this.state) {
        case 'title': {
          // slow attract pan
          this.camera.x = (Math.sin(this.stateTicks * 0.0032) * 0.5 + 0.5) * 120;
          this.tick += 1;
          this.updateAttractActors();
          FD.Renderer.updateWeather(this);
          if (input.wasPressed('start') || input.wasPressed('attack') || input.wasPressed('jump')) {
            FD.audio.unlock();
            FD.sfx('select');
            if (FD.Cinematic && !this.skipCinematic && !FD.assets.filmMode) {
              this.cinematicT = 0;
              this.setState('cinematic');
            } else {
              this.startStage();
            }
          }
          break;
        }
        case 'movie':
        case 'cinematic': {
          this.cinematicT += 1 / 60;
          FD.Renderer.updateWeather(this);
          if (this.cinematicT >= FD.Cinematic.duration || input.wasPressed('start') || input.wasPressed('attack')) {
            this.startStage();
          }
          break;
        }
        case 'intro': {
          this.tick += 1;
          this.player.hidden = false;
          FD.Renderer.updateWeather(this);
          if (this.stateTicks === 1) {
            FD.Actors.setAnim(this.player, 'walk');
          }
          if (this.stateTicks > 30 && this.stateTicks < 100) {
            this.player.x = FD.clamp(this.player.x + 0.6, 40, 260);
          }
          this.player.facing = 1;
          FD.Actors.advanceAnim(this.player);
          FD.Actors.advanceAnim(this.player);
          if (this.stateTicks > 170) {
            this.setState('playing');
            this.stageState.banner = 'GO';
            this.stageState.bannerTicks = 48;
          }
          break;
        }
        case 'playing': {
          this.updatePlay();
          break;
        }
        case 'paused': {
          if (input.wasPressed('pause') || input.wasPressed('start')) {
            this.setState('playing');
            FD.sfx('select');
          }
          break;
        }
        case 'stageclear': {
          this.tick += 1;
          FD.Actors.advanceAnim(this.player);
          FD.Renderer.updateWeather(this);
          this.updateEffects();
          if (this.stateTicks > 260) {
            this.setState('results');
          }
          break;
        }
        case 'results': {
          FD.Renderer.updateWeather(this);
          this.tick += 1;
          if (input.wasPressed('start') || input.wasPressed('attack')) {
            FD.sfx('select');
            this.startTitle();
          }
          break;
        }
        case 'gameover': {
          this.gameoverTicks += 1;
          this.tick += 1;
          FD.Renderer.updateWeather(this);
          this.updateEffects();
          if (this.gameoverTicks > 90 && (input.wasPressed('start') || input.wasPressed('attack'))) {
            FD.sfx('select');
            this.startStage();
          }
          break;
        }
        default:
          break;
      }
      input.endTick();
    }

    updateAttractActors() {
      if (!this.player) return;
      const p = this.player;
      p.x = 205 + Math.sin(this.stateTicks * 0.01) * 6;
      p.z = 236;
      p.facing = 1;
      FD.Actors.advanceAnim(p);
      if (!this.enemies.length) {
        const e = FD.Actors.createEnemy(this, 'rivet', 340, 222, { side: 1 });
        e.state = 'idle';
        e.decisionTicks = 9999;
        e.alpha = 1;
        e.z = 222;
        this.enemies.push(e);
      }
      for (const e of this.enemies) {
        e.x = 336 + Math.sin(this.stateTicks * 0.012 + 1) * 5;
        e.facing = -1;
        FD.Actors.advanceAnim(e);
      }
    }

    updatePlay() {
      const input = FD.input;
      if (input.wasPressed('pause')) {
        this.setState('paused');
        FD.sfx('select');
        return;
      }
      if (input.wasPressed('mute')) {
        FD.audio.setMuted(!FD.audio.muted);
      }
      if (input.wasPressed('debug')) {
        this.debug.showHitboxes = !this.debug.showHitboxes;
      }
      if (this.autopilot) this.applyAutopilot();
      if (this.hitstop > 0) {
        this.hitstop -= 1;
        return;
      }
      this.tick += 1;
      this.timerTicks -= 1;
      if (this.combo.timer > 0) {
        this.combo.timer -= 1;
        if (this.combo.timer === 0) this.combo.count = 0;
      }

      FD.Actors.updatePlayer(this, this.player);
      for (const e of this.enemies) FD.Actors.updateEnemy(this, e);
      if (this.player.state === 'dead') {
        this.gameoverTicks += 1;
        if (this.gameoverTicks > 110) {
          this.results = {
            score: this.score, timeLeft: Math.max(0, Math.ceil(this.timerTicks / 60)),
            hits: this.stats.hits, damageTaken: this.stats.damageTaken, cleared: false,
          };
          this.setState('gameover');
          FD.audio.duckMusic(false);
          return;
        }
      } else {
        this.gameoverTicks = 0;
      }
      // player-enemy body separation
      for (const e of this.enemies) {
        if (e.state === 'defeated' || e.state === 'fall') continue;
        if (Math.abs(e.x - this.player.x) < 20 && Math.abs(e.z - this.player.z) < 10 &&
            this.player.state !== 'attack' && this.player.state !== 'special' && this.player.state !== 'jump_attack') {
          const dir = FD.sign(this.player.x - e.x) || 1;
          this.player.x = FD.clamp(this.player.x + dir * 0.4, this.arena().minX, this.arena().maxX);
        }
      }
      FD.Actors.resolveHits(this);
      FD.Stage.update(this);
      this.updateEffects();
      FD.Renderer.updateWeather(this);
      if (this.timerTicks <= 0 && this.player.state !== 'dead') {
        FD.Actors.playerTakeHit(this, this.player, 999, { dir: 1, knockdown: true });
      }
    }

    updateEffects() {
      for (let i = this.effects.length - 1; i >= 0; i--) {
        const fx = this.effects[i];
        fx.t += 1;
        if (fx.t >= fx.life) this.effects.splice(i, 1);
      }
    }

    // ---------------------------------------------------------------- autopilot
    applyAutopilot() {
      const input = FD.input;
      const p = this.player;
      const plan = this.autopilotPlan;
      for (const a of ['left', 'right', 'up', 'down', 'attack', 'jump', 'special']) input.release(a);
      if (plan.attackCooldown > 0) plan.attackCooldown -= 1;
      if (plan.specialCooldown > 0) plan.specialCooldown -= 1;
      if (!p || p.state === 'dead') return;
      const busy = ['attack', 'special', 'jump_attack', 'hurt', 'fall', 'getup', 'land', 'victory'].includes(p.state);
      if (busy) return;

      // 1) survival: grab a health pickup when hurt
      if (p.health < 70) {
        let bestPick = null;
        let bestD = 1e9;
        for (const pick of this.pickups) {
          if (pick.type !== 'health') continue;
          const d = Math.abs(pick.x - p.x);
          if (d < 180 && d < bestD) { bestD = d; bestPick = pick; }
        }
        if (bestPick && bestD > 12) {
          if (Math.abs(bestPick.z - p.z) > 4) input.press(bestPick.z > p.z ? 'down' : 'up');
          input.press(bestPick.x > p.x ? 'right' : 'left');
          return;
        }
      }

      // 2) pick a fight target
      let target = null;
      let best = 1e9;
      for (const e of this.enemies) {
        if (e.state === 'defeated' || e.state === 'fall' || e.state === 'spawn') continue;
        const d = Math.abs(e.x - p.x) + Math.abs(e.z - p.z) * 0.6;
        if (d < best) { best = d; target = e; }
      }
      if (!target) {
        // 3) smash a crate that is right in front of us (but do not fixate)
        for (const prop of this.props) {
          if (prop.broken) continue;
          if ((prop.ignoredUntil || 0) > this.tick) continue;
          const d = Math.abs(prop.x - p.x);
          if (d < 52 && Math.abs(prop.z - p.z) < 10) {
            target = { x: prop.x, z: prop.z, prop };
            break;
          }
        }
      }
      if (!target) {
        input.press('right');
        return;
      }
      const dx = target.x - p.x;
      const dz = target.z - p.z;
      if (Math.abs(dz) > 4) input.press(dz > 0 ? 'down' : 'up');
      if (Math.abs(dx) > 36) {
        input.press(dx > 0 ? 'right' : 'left');
        return;
      }
      // in range: face the target and swing
      p.facing = dx >= 0 ? 1 : -1;
      if (Math.abs(dz) <= 12 && plan.attackCooldown <= 0) {
        input.press('attack');
        plan.attackCooldown = 6 + Math.floor(Math.random() * 4);
        if (target.prop) {
          target.prop.autopilotHits = (target.prop.autopilotHits || 0) + 1;
          if (target.prop.autopilotHits > 6) target.prop.ignoredUntil = this.tick + 240;
        }
      }
      const alive = this.enemies.filter((e) => e.state !== 'defeated' && e.state !== 'fall');
      if (alive.length >= 2 && plan.specialCooldown <= 0 && p.health > 50 && Math.random() < 0.025) {
        input.press('special');
        plan.specialCooldown = 120;
      }
    }

    // ---------------------------------------------------------------- render
    draw() {
      const ctx = this.ctx;
      ctx.imageSmoothingEnabled = false;
      switch (this.state) {
        case 'boot':
          ctx.fillStyle = '#05060c';
          ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
          FD.font.draw(ctx, 'LOADING', 240, 128, { align: 'center', color: 'cyan' });
          break;
        case 'title':
          this.drawTitle(ctx);
          break;
        case 'movie':
        case 'cinematic':
          FD.Cinematic.draw(this, ctx, this.cinematicT);
          break;
        case 'intro':
          FD.Renderer.draw(this);
          this.drawIntroOverlay(ctx);
          break;
        case 'playing':
          FD.Renderer.draw(this);
          break;
        case 'paused':
          FD.Renderer.draw(this);
          this.drawPauseOverlay(ctx);
          break;
        case 'stageclear':
          FD.Renderer.draw(this);
          this.drawStageClear(ctx);
          break;
        case 'results':
          this.drawResults(ctx);
          break;
        case 'gameover':
          FD.Renderer.draw(this);
          this.drawGameOver(ctx);
          break;
        default:
          break;
      }
    }

    drawTitle(ctx) {
      const cam = this.camera.x;
      this.camera.x = cam;
      FD.Renderer.draw(this);
      // darken for legibility
      ctx.fillStyle = 'rgba(4,6,14,0.45)';
      ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
      const logo = FD.assets.img('ui/logo.png');
      if (logo) {
        const bob = Math.sin(this.stateTicks * 0.04) * 2;
        ctx.drawImage(logo, 240 - logo.width / 2, 34 + bob);
      }
      const blink = Math.floor(this.stateTicks / 32) % 2 === 0;
      if (blink) {
        FD.font.draw(ctx, 'PRESS ENTER', 240, 156, { align: 'center', color: 'cyan', scale: 2 });
      }
      FD.font.draw(ctx, 'MOVE: ARROWS / WASD    ATTACK: J / Z    JUMP: K / X', 240, 194, {
        align: 'center', color: 'steel', scale: 1,
      });
      FD.font.draw(ctx, 'SPECIAL: L / C    PAUSE: ESC', 240, 206, { align: 'center', color: 'steel' });
      FD.font.draw(ctx, 'ORIGINAL BEAT \'EM UP  -  V1.0', 240, 250, { align: 'center', color: 'dim' });
      if (FD.Cinematic) {
        FD.font.draw(ctx, '12 SECOND INTRO MOVIE PLAYS ON START', 240, 226, { align: 'center', color: 'cyanDim' });
      }
    }

    drawIntroOverlay(ctx) {
      const t = this.stateTicks;
      if (t > 150) return;
      const fade = t < 20 ? t / 20 : t > 130 ? (150 - t) / 20 : 1;
      ctx.save();
      ctx.globalAlpha = fade;
      ctx.fillStyle = '#05070f';
      ctx.fillRect(0, 150, FD.VIEW_W, 74);
      ctx.fillStyle = '#63f7ff';
      ctx.fillRect(0, 150, FD.VIEW_W, 1);
      ctx.fillRect(0, 223, FD.VIEW_W, 1);
      FD.font.draw(ctx, 'STAGE 1', 240, 158, { align: 'center', color: 'amber', scale: 1 });
      FD.font.draw(ctx, FD.cfg.stage.title, 240, 172, { align: 'center', color: 'white', scale: 2 });
      FD.font.draw(ctx, FD.cfg.stage.subtitle, 240, 196, { align: 'center', color: 'cyanDim' });
      ctx.restore();
    }

    drawPauseOverlay(ctx) {
      ctx.save();
      ctx.fillStyle = 'rgba(4,6,14,0.62)';
      ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
      FD.font.draw(ctx, 'PAUSED', 240, 112, { align: 'center', color: 'cyan', scale: 3 });
      FD.font.draw(ctx, 'ESC TO RESUME', 240, 148, { align: 'center', color: 'steel' });
      FD.font.draw(ctx, 'ARROWS MOVE   J ATTACK   K JUMP   L SPECIAL', 240, 166, {
        align: 'center', color: 'dim',
      });
      ctx.restore();
    }

    drawStageClear(ctx) {
      const t = this.stateTicks;
      const a = FD.clamp(t / 30, 0, 1);
      ctx.save();
      ctx.globalAlpha = a;
      ctx.fillStyle = 'rgba(4,6,14,0.5)';
      ctx.fillRect(0, 86, FD.VIEW_W, 74);
      FD.font.draw(ctx, 'STAGE CLEAR', 240, 100, { align: 'center', color: 'amber', scale: 3 });
      FD.font.draw(ctx, `SCORE ${FD.pad(this.score, 6)}`, 240, 134, { align: 'center', color: 'white', scale: 1 });
      ctx.restore();
    }

    drawResults(ctx) {
      ctx.fillStyle = '#070a12';
      ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
      // slow rain behind the panel
      FD.Renderer.updateWeather(this);
      ctx.save();
      ctx.globalAlpha = 0.25;
      const near = FD.assets.img('stage/layers/near.png');
      if (near) ctx.drawImage(near, 900, 0, FD.VIEW_W, FD.VIEW_H, 0, 0, FD.VIEW_W, FD.VIEW_H);
      ctx.restore();
      ctx.fillStyle = 'rgba(6,8,16,0.72)';
      ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
      FD.font.draw(ctx, 'RESULTS', 240, 30, { align: 'center', color: 'cyan', scale: 3 });
      const r = this.results || { score: 0, timeLeft: 0, hits: 0, cleared: false };
      FD.font.draw(ctx, r.cleared ? 'RAIN DISTRICT CLEARED' : 'MISSION FAILED', 240, 66, {
        align: 'center', color: r.cleared ? 'amber' : 'red', scale: 1,
      });
      const rows = [
        ['SCORE', FD.pad(r.score, 6)],
        ['TIME LEFT', FD.pad(r.timeLeft, 2) + ' SEC'],
        ['HITS LANDED', FD.pad(r.hits, 3)],
      ];
      rows.forEach((row, i) => {
        const y = 96 + i * 18;
        FD.font.draw(ctx, row[0], 168, y, { color: 'steel' });
        FD.font.draw(ctx, row[1], 312, y, { color: 'white', align: 'right' });
      });
      FD.font.draw(ctx, 'THANKS FOR PLAYING', 240, 176, { align: 'center', color: 'dim' });
      if (Math.floor(this.stateTicks / 32) % 2 === 0) {
        FD.font.draw(ctx, 'PRESS ENTER', 240, 210, { align: 'center', color: 'cyan', scale: 2 });
      }
    }

    drawGameOver(ctx) {
      const t = this.gameoverTicks;
      const a = FD.clamp(t / 40, 0, 0.8);
      ctx.save();
      ctx.globalAlpha = a;
      ctx.fillStyle = '#0a0406';
      ctx.fillRect(0, 0, FD.VIEW_W, FD.VIEW_H);
      ctx.restore();
      FD.font.draw(ctx, 'GAME OVER', 240, 110, { align: 'center', color: 'red', scale: 3 });
      FD.font.draw(ctx, `SCORE ${FD.pad(this.score, 6)}`, 240, 146, { align: 'center', color: 'white' });
      if (this.gameoverTicks > 90 && Math.floor(this.stateTicks / 32) % 2 === 0) {
        FD.font.draw(ctx, 'PRESS ENTER TO RETRY', 240, 178, { align: 'center', color: 'cyan' });
      }
    }

    // ---------------------------------------------------------------- loop
    frame(now) {
      if (!this.running) return;
      if (!this.lastTime) this.lastTime = now;
      let dt = (now - this.lastTime) / 1000;
      this.lastTime = now;
      if (dt > 0.25) dt = 0.25;
      this.acc += dt;
      const step = 1 / FD.TICK_HZ;
      let guard = 0;
      while (this.acc >= step && guard < 6) {
        this.update();
        this.acc -= step;
        guard += 1;
      }
      this.draw();
      requestAnimationFrame((t) => this.frame(t));
    }

    startLoop() {
      this.running = true;
      this.lastTime = 0;
      requestAnimationFrame((t) => this.frame(t));
    }

    // Headless helper: run exact ticks without rendering.
    step(n = 1) {
      for (let i = 0; i < n; i++) this.update();
    }

    drawFrame() {
      this.draw();
    }
  }

  FD.Game = Game;

  FD.createGame = function (canvas) {
    const game = new Game(canvas);
    game.debug.invincible = !!(FD.cfg.presentation && FD.cfg.presentation.debug.invincible);
    game.skipCinematic = !!(FD.cfg.presentation && FD.cfg.presentation.debug.skipCinematic);
    return game;
  };

  FD.boot = async function (opts = {}) {
    const canvas = opts.canvas || document.getElementById('screen');
    const game = FD.createGame(canvas);
    const loading = document.getElementById('loading');
    const progress = document.getElementById('loading-bar');
    try {
      await FD.assets.load((n, total) => {
        if (progress) progress.style.width = `${Math.round((n / total) * 100)}%`;
      });
    } catch (err) {
      if (loading) loading.textContent = 'ASSET ERROR: ' + err.message;
      throw err;
    }
    FD.font.atlas('white');
    FD.audio.restoreMuted();
    if (loading) loading.classList.add('hidden');
    const startState = FD.cfg.presentation.debug.startAt || 'title';
    game.startTitle();
    if (startState === 'stage') game.startStage();
    if (startState === 'cinematic' && FD.Cinematic) game.setState('cinematic');
    const firstGesture = () => {
      FD.audio.unlock();
      window.removeEventListener('pointerdown', firstGesture);
      window.removeEventListener('keydown', firstGesture);
    };
    window.addEventListener('pointerdown', firstGesture);
    window.addEventListener('keydown', firstGesture);
    if (opts.autostart !== false) game.startLoop();
    FD.game = game;
    return game;
  };
})();
