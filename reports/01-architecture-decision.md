# 01 - Architecture Decision Record

## ADR-001: Engine for the vertical slice

**Status:** accepted (2026-10-19)
**Context:** the directive prefers OpenBOR, but OpenBOR cannot be obtained or executed in this sandbox (see `reports/01-engine-comparison.md`). The deliverable must be *runnable and tested*, not merely authored.

**Decision:** deliver a self-contained HTML5 Canvas2D engine (ES2020, no framework, no build step), with all gameplay data in JSON. The rendering code is written so that the same modules run in a browser *and* in a Node canvas harness, which is what produced every screenshot and both MP4 files.

**Consequences:**
- (+) The build is verifiable here: 23 automated tests, 11 screenshots, 2 rendered videos.
- (+) All art, audio and timing are original and editable.
- (-) No OpenBOR module is delivered. The port path is documented, not claimed.
- (-) Browser keyboard/gamepad input is the only control scheme (touch buttons provided).

## ADR-002: Data-driven actors instead of hard-coded logic

**Decision:** every frame count, frame duration, hit window, damage value, speed and spawn point lives in `config/*.json`. `tools/asset_pipeline/bundle_data.py` inlines them into `game/src/generated/data.js`.

**Consequences:**
- Changing a hitbox or a frame duration never requires touching the engine.
- The same numbers drive the sprite pipeline (which refuses to render a frame the config does not declare) and the runtime.
- Cost: one generated file the browser loads (`data.js`).

## ADR-003: Procedural sprite rig instead of hand-painted frames

**Decision:** `tools/asset_pipeline/rig.py` draws the characters from a skeleton (IK limbs, torso, head, boots, gauntlets) with a fixed palette and anchor. 84 frames are rendered from pose functions.

**Consequences:**
- Proportions, palette and pivot are identical across every frame by construction, which is exactly the failure mode hand-drawn sets usually suffer from.
- Regeneration is 2 seconds, so iteration is cheap.
- Cost: the style is deliberately compact/chunky; a hand-painted pass would add detail but break reproducibility.

## ADR-004: Verification through a headless harness, not a browser

**Decision:** `tools/capture/harness.js` mounts the production modules in Node with `@napi-rs/canvas` and a ~40-line DOM shim.

**Consequences:**
- Same code paths as the browser (no mocks).
- Deterministic frames for tests and video.
- The harness is not the browser: one DOM-API difference that the shim papers over could still break in a real browser. Mitigation: the served build was smoke-tested over HTTP and uses only standard Canvas2D APIs.
