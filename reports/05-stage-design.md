# 05 - Stage Design: RAIN DISTRICT, block 07

## Layout

| Property | Value |
|---|---|
| World width | 1800 px |
| Visible frame | 480x270 |
| Walkable lane (depth) | z = 204 .. 250 (46 px) |
| Player start | x 80, z 226 |
| Finish trigger | x 1740 |
| Camera | follows the player with a 22 px look-ahead, clamped to `worldWidth - 480` |
| Camera lock | active during waves, restores on clear |

## Layers

| Layer | Size | Parallax | Content |
|---|---|---|---|
| sky | 480x270 | 0.00 | indigo gradient, haze, small moon, stars |
| far | 512x270 | 0.15 | tileable skyline silhouettes with rooftop antennas |
| mid | 960x270 | 0.45 | tileable facades: window grid, shutters, awnings, 6 neon signs, pipes, AC units |
| near | 1800x270 | 1.00 | unique street: road, curb, slab sidewalk, puddles with reflected neon, lamps, bollards, bus stop |
| fg | 480x270 | 1.18 | overhead cables, paper lanterns, low bottom railing |

Rain, splashes, lightning (every 15-35 s with a short flash) and a vignette are
rendered by the engine, not baked into the layers.

## Waves

Spawn offsets are measured from the camera edge, so enemies always walk in from
off-screen regardless of the camera position.

| Wave | Trigger x | Enemies | Composition |
|---|---|---|---|
| 1 | 300 | 2 | rivet, rivet |
| 2 | 930 | 3 | rivet, **rivet_elite**, rivet |
| 3 | 1460 | 3 | **rivet_elite**, rivet, rivet |

Clearing a wave awards 500 points, unlocks the camera and advances the stage.
Touching x 1740 after the last wave ends the stage (`STAGE CLEAR` -> results).

## Props and pickups

| Prop | Position | HP | Drop |
|---|---|---|---|
| crate_a | 560, 240 | 2 | +24 HP |
| trash_a | 1080, 214 | 1 | +150 pts |
| crate_b | 1260, 246 | 2 | +24 HP |
| barrel_a | 1620, 218 | 2 | +24 HP |

Pickups blink during their last 2 seconds and are collected by proximity
(< 16 px horizontally, < 12 px in depth).

## Readability rules

* The fighting lane is the bottom third; background signage never crosses it.
* Foreground elements are overhead cables and a 8 px railing at the very bottom,
  never in front of a fighter's body.
* Neon reflections are drawn inside puddles only, so they cannot be confused
  with hit effects.
* Electric effects use the character's cyan, damage numbers use white/cyan for
  the player's hits and red for incoming damage.

## Preview

`artifacts/screenshots/03-stage-intro.png` and `04-combat.png` show the stage with
the HUD, waves and rain active; `artifacts/video/gameplay.mp4` shows it in motion.
