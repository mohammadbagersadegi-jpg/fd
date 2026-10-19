# 02 - Data Format Notes

## What we could and could not inspect

No ROM file exists in this environment, so **no binary container was decoded**. These notes describe (a) the formats this project *did* design and verify, and (b) what is known about the SoR1 pipeline from the disassembly listing only.

## Project formats (verified)

### `config/animation.json`
One entry per character. Each character declares its canvas and per-animation frame lists:

```json
"attack1": {
  "loop": false,
  "frames": [
    { "dur": 4 },
    { "dur": 3, "hit": { "x": 10, "y": -56, "w": 30, "h": 16 } },
    ...
  ]
}
```

* `dur` is in 60 Hz ticks.
* `hit` is a rectangle in **anchor-relative** coordinates: x grows forward, y grows down, origin at the feet. The engine mirrors x when the actor faces left.
* `"hit": { "radial": true }` marks the special's area attack.
* Frame count is implicit in the array length; the renderer, the spritesheet builder and the QA gate all read the same array, so they cannot disagree.

### Sprite frames
* `game/assets/characters/<id>/frames/<anim>/<anim>_NN.png`
* 128x96 RGBA, anchor at (64, 88), no premultiplied alpha, no colour profile.
* Artwork is authored inside a 112 px content box (x 0-111) and padded by 8 px on each side at export.
* Facing right is the source orientation; the engine mirrors with a canvas transform.

### Spritesheets
Horizontal strips, `frames * 128` wide, 96 tall — one PNG per animation.

### Stage
* `sky` 480x270 (no parallax), `far` 512x270 (0.15), `mid` 960x270 (0.45), `near` 1800x270 (1.0, unique), `fg` 480x270 (1.18).
* Tileable layers are authored to wrap seamlessly; `near` is unique content for the 1800 px stage.
* Props are individual PNGs with two damage stages.

### Font
`game/assets/fonts/font5x7.json` (data) and `.js` (browser twin). 67 glyphs, 5x7, 1 px tracking, exported from `tools/asset_pipeline/font5x7.py`.

## SoR1 observations (from the listing only)

* **Sprite mappings**: the object struct holds `Mappings` (dword) and `MappingsPtr` (word); the listing cross-references `SprMap_Axel`, `SprMap_Adam`, `SprMap_Blaze` as dword pointer tables (`off_1F20`), so each playable character has a mappings table rather than per-animation pointers.
* **Palettes**: `Palette` is a RAM symbol at `$FFFFF400`, and `Pal_ID_Enemy` / `Pal_Count` at `$FFFFFA6C` track which enemy palettes are loaded. The palette is uploaded to CRAM at runtime; the source data is compressed and was **not** decoded here.
* **Buffers**: `ELC_Buffer = $FF6800` is described in the listing as "Unpacks Enemy Loadcues here", and `NemesisDec_Buffer = $FF8000` names the Nemesis decompressor. Both are RAM buffers, not file formats.
* **Compression**: the Nemesis decompressor name appears only as a buffer label; the bitstream format was not re-derived in this project and is cited from the label, nothing more.
* **Audio**: not investigated.

## Rules this project follows to avoid fake precision

1. A format detail is only claimed if it is visible in the listing text or produced by our own tools.
2. RAM symbol locations are reported as RAM addresses, never as ROM offsets.
3. No extracted SoR1 art, palettes, sounds or level data is shipped.
