# 06 - Single-file build (`dist/neon-gauntlet.html`)

## Goal

A player should be able to download **one file**, double-click it and play,
with no server, no install and no network. Browsers refuse to load sibling
images from a `file://` page in some configurations, so every resource has to be
inside the document.

## How it is built

`tools/build_standalone.py`:

1. asks the runtime itself for the image list
   (`FD.assets.listImages(FD.assets.data())` through the Node harness), so the
   bundle can never drift from `assets.js`;
2. encodes each PNG as a `data:image/png;base64,...` URI and emits
   `window.FD_EMBED = { assets: { "<relative path>": "<data URI>" } }`;
3. replaces every `<script src="...">` in `game/index.html` with the file's
   source inline, in the original order;
4. asserts that no `src=`/`href=` outside `#` or `data:` remains;
5. writes `dist/neon-gauntlet.html`.

`game/src/assets.js` resolves images in this order: `FD_EMBED` / `FD_FILM`
data URI -> `assets/<path>` on the HTTP build. Nothing else in the engine
changes.

## Result

| Property | Value |
|---|---|
| File | `dist/neon-gauntlet.html` |
| Size | 0.44 MB |
| Scripts inlined | 12 (data bundle, font, core, assets, font renderer, input, audio, actors, stage, render, cinematic, main) |
| Images embedded | 102 (84 character frames, 5 stage layers, 9 props, 4 UI) |
| External references | 0 |
| Works from | `file://`, no server |

## Verification

`node tools/tests/standalone.js` executes the scripts extracted from the built
HTML with a DOM shim and a real PNG decoder, then plays the stage:

```
standalone: 102 images from data URIs, 0 external refs, stage CLEARED
```

The autopilot is stochastic, so the clear time and score vary per run
(observed 39.6-44.1 s). Every run must reach `results` with `cleared: true`,
otherwise the script exits non-zero. It writes `artifacts/standalone-test.json`
and `artifacts/standalone-proof.png` (the results screen rendered by the
single-file build).

## Bug found by this test

The first standalone run failed with
`TypeError: Cannot read properties of undefined (reading 'presentation')`:
`FD.boot()` calls `FD.createGame()` *before* `FD.assets.load()` resolves, and
`createGame()` reads `FD.cfg.presentation`, whose getter dereferenced
`FD.assets.dataRef` - still unset at that moment. The browser page had the same
defect; it was invisible in the tests because the harness assigns `dataRef`
before creating a game.

Fix in `game/src/assets.js`:

* `FD.assets.dataRef` / `fontRef` are populated at parse time from the bundle
  already on the page;
* the `FD.cfg` getters return `null` instead of throwing when the bundle is
  absent.

Regression coverage: the 23 module tests (`npm test`) plus
`node tools/tests/standalone.js` now exercise the real boot order.

## Not embedded

* **The MP4** (`cinematic/rendered-video.mp4`, 3.2 MB): a canvas game cannot play
  an MP4 inline; the intro is drawn by `game/src/cinematic.js` from the same
  shots, and the MP4 remains a separate download.
* **The exported gameplay video** and screenshots - evidence artefacts, not game
  content.
* **The development server** - not needed for the single file.

## Licensing

The single file contains only original code and original generated art from this
repository. No reference-game asset is embedded.
