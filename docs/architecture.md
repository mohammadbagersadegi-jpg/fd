# Architecture

## Runtime (browser or headless Node)

```
index.html
  └─ src/generated/data.js      config bundle (built from config/*.json)
  └─ assets/fonts/font5x7.js    bitmap font data
  └─ src/core.js                math, RNG, sfx queue, constants
  └─ src/assets.js              image loading, config accessors
  └─ src/font.js                5x7 text renderer with colour atlases
  └─ src/input.js               keyboard + gamepad + touch -> abstract actions
  └─ src/audio.js               procedural WebAudio SFX and stage track
  └─ src/actors.js              player + enemy state machines, hit resolution
  └─ src/stage.js               waves, props, pickups, camera, arena
  └─ src/render.js              parallax, rain, depth sort, HUD, effects
  └─ src/cinematic.js           12 s intro drawn from the same assets
  └─ src/main.js                fixed 60 Hz loop, scenes, autopilot
```

Frame model: a fixed 1/60 s simulation step, decoupled from rendering with an
accumulator (max 6 catch-up steps per frame). All gameplay state is plain data on
the `Game` instance, so the headless harness can step it without a display.

## Data flow

`config/*.json` -> `bundle_data.py` -> `data.js` -> `FD.assets.dataRef`.

Nothing in `game/src` contains a balance number. The only literals in engine code
are structural (e.g. which state follows which), never speeds, damage or timings.

## Scene flow

```
boot -> title -> cinematic -> intro -> playing <-> paused
                                        |  \-> stageclear -> results -> title
                                        \-> gameover (after death) -> retry -> intro
```

## Coordinate model

* `x` - world position along the street.
* `z` - depth; larger z = closer to the camera (drawn later).
* `yOffset` - height above the ground (jump/knockback), 0 = grounded.
* The sprite anchor is the character's feet, so a frame is drawn at
  `(x - anchorX, z - anchorY - yOffset)` and mirrored around the anchor when
  facing left.
* Hit rectangles in `animation.json` are anchor-relative; `Actors.hitBoxFor`
  mirrors them for left-facing attacks and expands them by the depth tolerance.

## Testing

* `tools/tests/run.js` - 23 behavioural and asset tests, run in the headless
  harness against the production modules.
* `tools/validation/validate_assets.py` - frame/sheet/manifest QA gate.
* `tools/capture/harness.js` - ~60 line DOM shim (document, Image, localStorage,
  requestAnimationFrame, navigator) that mounts `game/src/*` on `@napi-rs/canvas`.

## Why a canvas shim instead of a browser

The sandbox cannot run headless Chromium (missing NSS/NSPR libraries, no
package manager access) and cannot download the OpenBOR binary. `@napi-rs/canvas`
implements the same Canvas2D API in native code, so the identical modules render
to a buffer that is both screenshotted and piped into ffmpeg.
