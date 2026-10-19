# 02 - State Machines

The machine-readable version with every transition is `reports/02-state-machines.json`.
The SoR1 mapping column refers to evidence record **SOR1-E006** (`off_1CE2` handler table).

## Player (VOLT)

```
            +------------------- special (90t cooldown) -------------------+
            |                                                                v
 IDLE <-> WALK --attack--> ATTACK1 --buffer--> ATTACK2 --buffer--> ATTACK3 --> IDLE
   |  \                        |                     |                  |
   |   \--jump--> JUMP --attack--> JUMP_ATTACK --land--> LAND --4t--> IDLE
   |                      \--ground contact--> LAND
   +--special--> SPECIAL (radial hit frames 2-3, 20t i-frames) --> IDLE
   |
   +--hit--> HURT (14t) --> IDLE
   +--hit(heavy)/hp0--> FALL --land--> KO floor (82t) --> GETUP (45t i-frames) --> IDLE
                                                       \--> DEAD (hp0) --> GAME OVER
 STAGE CLEAR --> VICTORY (loop)
```

Invariants enforced by the engine (and by the tests):

1. An attack can hit each target at most once (`hitSet` is cleared when a *new* attack starts, never mid-attack).
2. Combo input is only accepted while `attack` is in an attack state; the chain fires at `chainAtTick` (the tick after the last active frame).
3. `yOffset` returns to exactly 0 on landing; landing has a 4-tick recovery before movement resumes.
4. `invulnTicks` blocks both damage and the state change.
5. Dead players cannot act; the camera and waves stop.

## Enemy (RIVET / RIVET-S)

```
 SPAWN (walk in, fade) --> APPROACH (flank, keep spacing)
                             |  ^
                    attack   |  |  frames end / cooldown
                             v  |
                           ATTACK --hit--> player HURT
                             |
      hit <----------------- + --> HURT --> APPROACH
      heavy hit / hp 0 -----------> FALL --land--> (hp>0) GETUP --> APPROACH
                                             \--> (hp0) DEFEATED (fade, removed)
```

Anti-degeneracy measures (all tested manually in the recorded gameplay reel):

* side flipping when another enemy already occupies a flank,
* 22 %/16 % chance to break off after an attack,
* 22 px personal-space push between enemies,
* enemies stop attacking a knocked-down player (`playerVulnerable` check),
* `safeTime` prevents an attack during the first 30 ticks after spawning.

## SoR1 correspondence

| This project | SoR1 handler (evidence SOR1-E006) |
|---|---|
| IDLE | Obj_Stand (2/3) |
| WALK | Obj_Player_Walk (6-F) |
| ATTACK1-3 | Obj_Attack (18-1D) |
| JUMP / JUMP_ATTACK | Obj_Jump_1/2 (10-13), Obj_Jump_Attack (16/17) |
| LAND | Obj_Jump_Land (14/15) |
| HURT | Obj_Player_Hit (5A/5B) |
| FALL | Obj_Player_KO (5C/5D) |
| GETUP | Obj_Player_GetUp (5E) |
| DEAD | Obj_Player_Death (56-59) |

The naming was modernised and the SPECIAL state has no direct SoR1 equivalent (it sits closest to `Obj_Player_Pose`, 4/5). That is recorded as an inferred, not verified, mapping.
