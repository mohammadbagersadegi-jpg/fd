// Keyboard + gamepad input mapped to five abstract actions.
(function () {
  'use strict';
  const FD = window.FD;

  const KEYMAP = {
    ArrowLeft: 'left', KeyA: 'left',
    ArrowRight: 'right', KeyD: 'right',
    ArrowUp: 'up', KeyW: 'up',
    ArrowDown: 'down', KeyS: 'down',
    KeyJ: 'attack', KeyZ: 'attack',
    KeyK: 'jump', KeyX: 'jump', Space: 'jump',
    KeyL: 'special', KeyC: 'special',
    Enter: 'start', Escape: 'pause',
    KeyP: 'pause', KeyH: 'help', KeyM: 'mute', F2: 'debug', Backquote: 'debug',
  };

  const BTN = {
    0: 'attack', 1: 'jump', 2: 'special', 3: 'special',
    9: 'start', 8: 'pause',
    12: 'up', 13: 'down', 14: 'left', 15: 'right',
  };

  const state = {
    held: Object.create(null),
    pressed: Object.create(null),
    released: Object.create(null),
    anyPressed: false,
    enabled: true,
    touch: false,
    lastDevice: 'keyboard',
  };

  const actions = ['left', 'right', 'up', 'down', 'attack', 'jump', 'special', 'start', 'pause', 'help', 'mute', 'debug'];

  function press(action) {
    if (!action) return;
    if (!state.held[action]) state.pressed[action] = true;
    state.held[action] = true;
    state.anyPressed = true;
  }
  function release(action) {
    if (!action) return;
    if (state.held[action]) state.released[action] = true;
    state.held[action] = false;
  }

  window.addEventListener('keydown', (e) => {
    const action = KEYMAP[e.code];
    if (action) {
      e.preventDefault();
      if (!e.repeat) press(action);
      state.lastDevice = 'keyboard';
    }
    if (e.code === 'Enter' || e.code === 'Space') e.preventDefault();
  }, { passive: false });

  window.addEventListener('keyup', (e) => {
    const action = KEYMAP[e.code];
    if (action) {
      e.preventDefault();
      release(action);
    }
  }, { passive: false });

  window.addEventListener('blur', () => {
    actions.forEach(release);
    state.held = Object.create(null);
  });

  // Simple on-screen controls for touch devices.
  function bindTouch(root) {
    const buttons = root.querySelectorAll('[data-action]');
    buttons.forEach((btn) => {
      const action = btn.getAttribute('data-action');
      const down = (e) => { e.preventDefault(); state.touch = true; press(action); btn.classList.add('active'); };
      const up = (e) => { e.preventDefault(); release(action); btn.classList.remove('active'); };
      btn.addEventListener('touchstart', down, { passive: false });
      btn.addEventListener('touchend', up, { passive: false });
      btn.addEventListener('touchcancel', up, { passive: false });
      btn.addEventListener('mousedown', down);
      btn.addEventListener('mouseup', up);
      btn.addEventListener('mouseleave', up);
    });
  }

  const input = {
    state,
    actions,
    press,
    release,
    bindTouch,
    isDown: (a) => !!state.held[a],
    wasPressed: (a) => !!state.pressed[a],
    wasReleased: (a) => !!state.released[a],
    axisX() { return (state.held.right ? 1 : 0) - (state.held.left ? 1 : 0); },
    axisY() { return (state.held.down ? 1 : 0) - (state.held.up ? 1 : 0); },
    pollGamepad() {
      if (!navigator.getGamepads) return;
      const pads = navigator.getGamepads();
      for (const pad of pads) {
        if (!pad) continue;
        for (const [index, action] of Object.entries(BTN)) {
          const b = pad.buttons[index];
          if (!b) continue;
          if (b.pressed) press(action);
          else release(action);
        }
        const ax = pad.axes[0] || 0;
        const ay = pad.axes[1] || 0;
        if (ax < -0.35) press('left'); else if (ax > 0.35) press('right');
        if (ay < -0.35) press('up'); else if (ay > 0.35) press('down');
        if (ax >= -0.35 && ax <= 0.35) { release('left'); release('right'); }
        if (ay >= -0.35 && ay <= 0.35) { release('up'); release('down'); }
        state.lastDevice = 'gamepad';
      }
    },
    endTick() {
      state.pressed = Object.create(null);
      state.released = Object.create(null);
      state.anyPressed = false;
    },
  };

  FD.input = input;
})();
