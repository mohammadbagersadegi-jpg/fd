# Calibration

Measured values are written by the test suite to `artifacts/calibration.json`
every time `node tools/tests/run.js` runs. The table below is generated from the
last run of the delivered build.

| Measurement | How it is measured | Last value |
|---|---|---|
| Walk speed | hold right for 120 ticks, divide distance | 1.88 px/tick |
| Jump apex | highest `yOffset` during a jump | 21.6 px |
| Air time | ticks until the player is grounded again | 18 ticks (0.300 s) |
| Attack active window | ticks where the current frame declares a hit box | 6 ticks (jump attack: 8, attack3/special: 7/12) |
| Attack total | ticks from press to idle | 22 ticks |
| Hurt -> control | 14 tick flinch + idle | 14 ticks |
| Knockdown -> control | fall + 82 tick floor + 30 tick get-up | ~120 ticks |
| Special cooldown | ticks until the special can fire again | 90 ticks |

SoR1 reference (derived from the disassembly, `reports/02-physics-parameters.json`):

| SoR1 | Value |
|---|---|
| walk speed | 3.0 px/tick |
| depth speed | 12.0 px/tick |
| jump velocity | -7.0 px/tick |
| gravity | 0.90625 px/tick² |
| jump apex | 27.03 px |
| air time | 15.45 ticks |
| hit box | 40x32 px at (-20, -16) |
| depth tolerance | ±8 |

## Comparability statement

The two games run at different resolutions (320x224 vs 480x270), with different
character heights and lane geometry, and the new game adds hit-stop. The
delivered build therefore does **not** claim frame-for-frame parity with SoR1.
What is claimed:

1. SoR1's extracted constants are recorded with their evidence.
2. The new game's measured behaviour is recorded and reproducible.
3. Every deliberate deviation is listed with a reason in `reports/03-physics-and-feel.md`.
