# 02 - Reverse Engineering Notes: Streets of Rage 1

## Scope and honesty statement

* **No ROM was downloaded, provided or analysed.** The project has no access to a legally provided cartridge dump in this sandbox.
* Every address quoted below is the **CPU address printed by IDA Pro** in the public text listing `Assemblies/Streets of Rage (JUE) (REV 00) [!].asm` from the `gsaurus/sor-disassemblies` repository (72,919 lines). The listing header records `Input MD5 : 569CFEC15813294A8F0CF88CCCC8C151`, `CRC32 : BFF227C6`.
* The disassembly is treated as a *secondary source*. Labels such as `Chk_Hit` or `Obj_Player_Walk` were written by the disassembly author, not by Sega; they are strong hints, not ground truth.
* Because the repository targets "(JUE) (REV 00)", no claim in this project applies to REV 01, the Japanese *Bare Knuckle* release, or the 8-bit versions.
* Confidence labels: **verified** (arithmetic or table content read directly), **inferred** (derived from surrounding code), **unverified** (plausible, not tested).

## 1. Object model

The disassembly defines an object struct ("SST") at the top of the file (listing lines ~140-200). Fields that matter for this project:

| Offset | Name in listing | Meaning | Verification |
|---|---|---|---|
| `$00` | ObjID1 | object type | verified |
| `$02/$03` | Col_ID_Hit / Col_ID_Atk | collision identity | verified |
| `$04/$08` | Mappings / MappingsPtr | sprite mappings | verified |
| `$0A` | Frame | current frame index | verified |
| `$0C` | Animation | current animation id | verified |
| `$0D` | FrameTimer | per-frame countdown | verified |
| `$10` | XPos | world X (dword) | verified |
| `$14` | YPos | Y (screen space) | verified |
| `$18` | *(unnamed in struct)* | depth-like axis used by `Chk_Hit` | inferred |
| `$1C/$20/$24` | X_Inertia / Y_Inertia / Jump_Inertia | 16.16 velocities | verified |
| `$30` | ObjMode | state id | verified |
| `$32` | Health | word | verified |
| `$34` | AtkDamage | byte | verified |

## 2. State machine

`off_1CE2` (listing line 3425) is a word table of handlers indexed by `ObjMode`. Consecutive modes share a handler because the low bit is used as the facing flag (the code does `andi.b #$FE` before indexing in several routines).

| ObjMode (hex) | Handler | Project state |
|---|---|---|
| 0, 1 | Init_Stand | spawn |
| 2, 3 | Obj_Stand | idle |
| 4, 5 | Obj_Player_Pose | taunt / special pose |
| 6-F | Obj_Player_Walk | walk |
| 10, 11 | Obj_Jump_1 | jump (launch) |
| 12, 13 | Obj_Jump_2 | jump (air) |
| 14, 15 | Obj_Jump_Land | land |
| 16, 17 | Obj_Jump_Attack | jump attack |
| 18-1D | Obj_Attack | attack frames |
| 1E, 1F | Obj_Attack_KO | knockdown attack |
| 22, 23 | Obj_BackAttack_1 | rear attack wind-up |
| 24, 25 | Obj_BackAttack_2 | rear attack |
| 30-33 | Obj_Player_Weapon / _Walk | weapon states |
| 3C-43 | Obj_Player_Weapon_Jump_* | weapon jump states |
| 56-59 | Obj_Player_Death / _Death_2 | death |
| 5A, 5B | Obj_Player_Hit | hurt |
| 5C, 5D | Obj_Player_KO | knockdown |
| 5E | Obj_Player_GetUp | get up |

This mapping is what the delivered state machine follows (`IDLE, WALK, ATTACK1-3, JUMP, JUMP_ATTACK, SPECIAL, HURT, FALL, GETUP, DEAD`), with names modernised but transitions preserved.

## 3. Physics values that were actually extracted

`Update_Inertia` (line 6656) reads two bytes per mode from a per-character table and expands them to 16.16:

```
moveq #0,d1
move.b ObjID2(a0),d1      ; character id
lsl.w #2,d1
movea.l off_3664(pc,d1.w),a1
move.b ObjMode(a0),d1
andi.b #$FE,d1
...
move.b (a1,d1.w),d2       ; X step byte
ext.w d2
swap  d2
asr.l #4,d2               ; v = byte << 16 >> 4 = byte * 4096
move.l d2,X_Inertia(a0)
...
move.b 1(a1,d1.w),d2      ; depth step byte
```

For the walk entries (mode 6..F) the table bytes are `$30` and `$C0`, giving:

* horizontal walk speed = `$30 << 16 >> 4` = `$30000` = **3.0 px/tick**
* depth walk speed = `$C0 << 16 >> 4` = `$C0000` = **12.0 px/tick**

Jump constants (verified literals):

| What | Literal | 16.16 value | Where |
|---|---|---|---|
| initial jump velocity (up) | `#$FFF90000` | -7.0 px/tick | `loc_20BA`, line 3860 |
| gravity per tick | `#$E800` | 0.90625 px/tick² | `sub_389A`, line 6872 |
| downward speed clamp | `#$C0000` | 12.0 px/tick | `sub_3886`, line 6849 |
| jump attack forward push | `#$7000` | 0.4375 px/tick | `loc_20BA`, line 3861 |

Derived (pure arithmetic, no ROM needed):

* apex = v² / 2g = 49 / 1.8125 = **27.03 px**
* airtime = 2v / g = 14 / 0.90625 = **15.45 ticks** (≈0.26 s at 60 Hz)

## 4. Hit detection

`Chk_Hit` (line 6007) builds a rectangle around the attacker and scans the enemy SST array:

```
move.w XPos(a0),d1 ; addi.w #-$14,d1     ; left  = x - 20
move.w d1,d2       ; addi.w #$28,d2      ; right = left + 40
move.w YPos(a0),d3 ; addi.w #-$10,d3     ; top   = y - 16
move.w d3,d4       ; addi.w #$20,d4      ; bottom = top + 32
move.w $18(a0),d5  ; addi.w #-8,d5       ; depth window -8
move.w d5,d6       ; addq.w #8,d6        ; ... +8
```

So a SoR1 attack body is **40x32 px** offset **(-20, -16)** from the attacker position, with a **±8** depth tolerance. `Chk_Attack_Player` (line 6466) applies the damage byte, calls `Update_HealthBar` and returns `-1` when health reaches 0, which is how knockouts propagate.

## 5. Timing model

`FrameTimer` is a per-object byte that counts down every tick (`Obj_Stand`: `subq.b #1,FrameTimer(a0) ; bne ...`). Animation speed is therefore per-animation, data-driven, and expressed in 60 Hz ticks — exactly the model used by `config/animation.json` (`frames[].dur`).

## 6. What was *not* extracted

* Per-character damage tables (they live in animation data blobs; not parsed).
* Sprite/palette compression formats (no ROM, so tile decoding was out of scope).
* Enemy AI tables and stage event scripts.
* Audio driver behaviour.

These are marked as unknown rather than guessed. The delivered game deliberately uses **independent, documented numbers** tuned for 480x270/60 Hz, not ROM values copied blindly (see §7).

## 7. Translation to the new game (compatibility layer)

SoR1 runs at 320x224 with characters roughly 56-64 px tall. The new game renders at 480x270 with the same character height, so a direct copy of "3 px/tick" would feel sluggish for its screen size. The translation rule applied:

| Parameter | SoR1 (evidence) | New game | Why |
|---|---|---|---|
| walk speed | 3.0 px/tick | 1.9 px/tick | different screen scale and character-to-screen ratio |
| depth speed | 12.0 px/tick | 1.45 px/tick | SoR1 uses a much larger lane; 12 px would cross the 46 px lane in 4 ticks |
| jump velocity | -7.0 | -5.2 | keeps apex ≈22 px which reads better at 270 px height |
| gravity | 0.90625 | 0.56 | lengthens airtime to 18 ticks for readability |
| depth tolerance | ±8 | ±15 | the new lane is 46 px tall, SoR1's is ~40 px but characters are packed differently |
| hit box | 40x32 at (-20,-16) | 24-38 x 16-20 per frame | per-frame boxes instead of a single generic box |

All numbers are in `config/movement.json`, `config/collision.json`, `config/combat.json` and are covered by `artifacts/calibration.json`.
