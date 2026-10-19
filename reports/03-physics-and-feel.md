# 03 - Compatibility Layer: from SoR1 numbers to this game's numbers

This report exists because copying SoR1 constants directly into a 480x270 game
with a 46 px lane would not reproduce the *feel* the constants create in a
320x224 game. The target is behavioural compatibility, not numeric equality.

## Calibration table (measured, not guessed)

Source of every "measured" value: `artifacts/calibration.json`, produced by the
calibration tests in `tools/tests/run.js` on the actual build.

| Parameter | SoR1 reference | New game (measured) | Ratio / note |
|---|---|---|---|
| Walk speed | 3.0 px/tick (SOR1-E001) | **1.88 px/tick** | 0.63x; the new character is 56 px on a 270 px screen vs 64 px on 224 |
| Depth speed | 12 px/tick (SOR1-E002) | **1.45 px/tick** | intentional: the lane is 46 px, SoR1's depth travel is a different scale |
| Jump apex | 27.03 px (SOR1-E003 derived) | **21.6 px** | keeps a full jump inside one screen third |
| Air time | 15.45 ticks (SOR1-E003 derived) | **18 ticks** (0.30 s) | slightly floatier, reads better at this scale |
| Gravity | 0.90625 px/t² | **0.56 px/t²** | -38 % |
| Attack total | not extracted | **22 ticks** (0.37 s) | jab |
| Attack active window | generic 40x32 box (SOR1-E004) | **6 ticks**, box 30x16 per frame | per-frame boxes instead of one box |
| Hit-stop | not in SoR1 | **3-7 ticks** | added for impact; presentation only |
| Depth tolerance | ±8 (SOR1-E005) | **±15 / ±17** | lane is proportionally taller |
| Player i-frames after hurt | not extracted | **38 ticks** | prevents stun-lock |
| Get-up invulnerability | not extracted | **45 ticks** | prevents wake-up loops |

## Reading of the constants

SoR1's jump is very snappy: v=7 and g=0.906 means the character reaches the apex
in 7.7 ticks (0.13 s). At this project's screen scale that would make the jump
almost invisible, so the new values trade a little realism for readability.

SoR1's depth speed of 12 px/tick is roughly 4x its walk speed. In this project the
lane is only 46 px tall; a 4x depth speed would teleport the player between the
top and bottom of the lane in 4 ticks, so depth speed was set *below* walk speed.
This is a deliberate deviation, documented here so it is not mistaken for an
extraction error.

## Where the numbers live

| File | Contents |
|---|---|
| `config/movement.json` | walk/depth speed, acceleration, jump, gravity, camera |
| `config/collision.json` | body sizes, depth tolerances, separation rules |
| `config/combat.json` | damage, hit-stop, knockback, cooldowns, enemy archetypes |
| `config/animation.json` | frame counts, frame durations, per-frame hit rectangles |
| `config/stage.json` | lane bounds, waves, spawn points, props, pickups |

Editing a value in one of these files and re-running
`python3 tools/asset_pipeline/build_all.py` (or just reloading the page, because
`data.js` is regenerated) changes the game and the tests together. No number is
duplicated in engine code.
