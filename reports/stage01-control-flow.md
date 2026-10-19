# Stage 1 — control flow: scene dispatch, wave blocks and ELC cursor

**Target:** *Streets of Rage* (JUE REV 00) listing
`Assemblies/Streets of Rage (JUE) (REV 00) [!].asm` (72 920 lines, SHA-256
`b21835df76ba33bc11c0d922bada8947d19106c8f112b61d8715abab4704ac16`).
All "L###" references are line numbers in that file; label names carry the
ROM address (`sub_436` = `$436`, `loc_59C` = `$59C`, …).

**Result in one line:** the four decoded blocks are processed by the ordinary
wave pipeline — block 1 at level start and blocks 2–4 by three
`EnemySpawn_Scene` calls at `Scene` 0, 1 and 2 — and the `Scene >= 3` guard
sends the pipeline to the **boss-arrival state** without spawning a fifth
block. The first column of blocks 1–4 uses `$0300/$0600/$0900/$0C00`; the
`$0x00` step is explained by `add.b d2,($FFFFFB12).w` hitting the **high**
byte of the word (68000 big-endian), not the low byte.

---

## 1. State register: `$FFFFFB14` / `$FFFFFB15`

`sub_436` (L595) dispatches on the **low byte** of the word at `$FFFFFB14`:

```
595 sub_436:
600     move.b  ($FFFFFB15).w,d0     ; low byte = state value
601     move.w  off_44C(pc,d0.w),d0
602     jmp     off_44C(pc,d0.w)
```

Because the first lookup is a **byte** offset into a table of **words**, the
state value is `2 × table index`. All writers use even values, and the
high byte holds flags set with `bset #n,(…).w` (word bit numbering puts bit 0
at the MSB, so `bset #3` touches the high byte = flag bit, never the state).

| Index | State byte | Target | Role |
| ---: | ---: | --- | --- |
| 0 | 0 | `EnemySpawn_Scene` (L777) | spawn the next wave block (3× `Init_Enemy`) |
| 1 | 2 | `loc_6A6` (L841) | camera-lock check → state 2 |
| 2 | 4 | `loc_784` (L945) | timed-list runner |
| 3 | 6 | `EnemySpawn_Chk_Pal` (L1017) | deferred header + palette scan |
| 4 | 8 | `loc_936` (L1151) | deferred palette selection |
| 5 | $A | `loc_B76` (L1413) | deferred spawn + list compaction |
| 6 | $C | `loc_C28` (L1483) | wait for palette match / wave end |
| 7 | $E | `loc_59C` (L745) | **boss arrival** (boss palette + art) |
| 8 | $10 | `loc_748` (L921) | timed wait before state 2 |
| 9 | $12 | `Write_Art` (L1633) | art upload, then camera gate |
| 10 | $14 | `loc_4CA` (L663) | player-death / continue path |
| 11 | $16 | `loc_464` (L626) | boss-defeat / Mr. X offer path |

`off_44C` is the 12-word table at L610. This is the key that unlocks every
`move.w #$N,($FFFFFB14)` in the listing: `$12` is not "18" of anything, it is
**index 9**.

---

## 2. Frame order: camera before ELC

`GameMode_InGame` (L30262) runs:

| Order | Line | Instruction | Effect |
| ---: | ---: | --- | --- |
| 1 | L30282 | `jsr Update_PlayerObj(pc)` | player logic |
| 2 | L20003 | inside `Update_PlayerObj`: `jsr Update_Screen_Pos` | camera machine |
| 3 | L44518 | `Update_Screen_Pos` → `sub_18C22` | camera states |
| 4 | L44657 | `off_18C34[0..1]` → `sub_19570` | consumes `$FFFA0D` bit 0, **`Scene++`**, new gate |
| 5 | L30289 | `jmp (sub_436).l` | ELC state machine |

`Update_PlayerObj` only calls `Update_Screen_Pos` when
`GameMode == $14` or `$16` (L19981–L20003), which is exactly the in-game mode.
The alternate in-game entry `loc_10920` (L30380) also calls
`Update_Screen_Pos` **before** `sub_436` (L30383, L30386).

**Consequence:** a gate request raised during ELC processing in frame *N*
(`move.b #1,$FFFFFA0D` at L1730) is consumed at the start of frame *N+1*, so
`Scene` is incremented **before** the ELC state machine runs that frame.

---

## 3. Level start (block 1)

`Init_LevelStart` (L30087):

| Line | Instruction | State before | Operation | State after |
| ---: | --- | --- | --- | --- |
| L30103 | `clr.w (Scene).w` | Scene = whatever the previous round left | reset | **Scene = 0** |
| L30106 | `move.b #1,($FFFFFA1F).w` | — | screen-busy path | `$FFFA1F = 1` |
| L30115 | `jsr Load_Enemy_Into_RAM` | ELC decoded into `$FF6800` | see below | — |

`Load_Enemy_Into_RAM` (L1779):

| Line | Instruction | Inputs | Operation | Outputs / next |
| ---: | --- | --- | --- | --- |
| L1811 | `lea (off_1C1C4).l,a1` | Level | pick round table | a1 = `off_1C1D4` |
| L1819 | `move.l (a1)+,($FFFFFC14).w` | descriptor[Scene=0] | cursor := `$FF6800` | `Cur_ELC_Adr = $FF6800` |
| L1820 | `move.w (a1)+,d0` | descriptor | geometry selector = 0 | d0 = 0 |
| L1822-23 | `move.w (a2,d0.w),$FFFB20` / `2(a2,d0.w),$FFFB12` | `word_1C1BC` | stride = 1, base = `$0300` | `$FFFB20=1`, `$FFFB12=$0300` |
| L1825 | `jsr Update_Enemy_Pal` | descriptor bytes 0–5 | palettes | `$FFFA60..$FFFA63`, `$FFFA6A` |
| L1826 | `jsr Init_Enemy` | cursor | block 1, column 0 | cursor after column 0 |
| L1828 | `add.b d2,($FFFFFB12).w` | d2 = 1 | **high byte** += 1 | base = `$0400` |
| L1829-1832 | `Init_Enemy` ×2 | cursor | columns 1, 2 | cursor after block 1 |
| L1856-57 | `move.w #$12,$FFFB14; bset #2,$FFFB14` | — | state 9 (Write_Art), flag 2 set | next: `jmp Write_Art` (L1860) |
| L1717 `loc_DF4` | after art | flag 2 **set** at level start | pending bit **not** set | state 1 (`#2`, L1735) |

So at level start `Scene = 0` and only block 1 is consumed. The camera does
**not** open a new corridor yet: this is exactly why the player is clamped
until the first wave dies (third-party runtime: stop at x = 1504 = `$4C0+$120`).

---

## 4. Wave clear → next block (blocks 2, 3, 4)

When the deferred list is exhausted and `$FFFFFB1E` (live enemy counter)
reaches zero, one of

* `loc_C1E` (L1479) — `clr.w $FFFB14`,
* `loc_C4E` (L1502) — `clr.w $FFFB14`,
* `loc_910` (L1140) — `clr.w $FFFB14`

sets **state 0**. The next `sub_436` call enters `EnemySpawn_Scene` (L777):

| Line | Instruction | State before | Operation | State after |
| ---: | --- | --- | --- | --- |
| L785 | `lea off_1C1C4; … a1 = table[Level]` | Level | round table | a1 |
| L790-793 | `a1 = a1 + 2*(Scene+1)` | Scene | **palette descriptor for Scene+1** | a1 |
| L794 | `jsr Update_Enemy_Pal` | descriptor | writes palettes | `Pal_Correct`, `$FFFA6A` |
| L796-800 | `cmpi.w #4,(Level); bcs loc_67A; …` | Level | branch tree | — |
| L824-826 | `cmpi.w #3,(Scene).w; bcc.s loc_646` | **Scene** | guard (L825) | if Scene ≥ 3 → state 7 |
| L828-837 | `Init_Enemy` ×3 + `add.b d2,$FFFB12` | cursor | spawn one block | cursor after block |
| L837 | `move.w #$12,$FFFB14` | — | state 9 | Write_Art |
| L1717 | art done | flag 2 clear (cleared by `#$12`) | `move.b #1,$FFFA0D` | pending set → next frame `Scene++` |

`Init_Enemy` (L1557) consumes exactly one count word + `count+1` six-byte
records and then stores the cursor (L1612). Three calls per scene = three
batch columns.

### 4.1 The dispatch table for round 1

| Spawned block | Caller | Scene at call | Palette lookup (Scene+1) | Gate opened afterwards |
| ---: | --- | ---: | ---: | --- |
| 1 | `Load_Enemy_Into_RAM` | 0 | entry 0 (cursor + geometry + palette) | none (flag 2 blocks `$FFFA0D`) |
| 2 | `EnemySpawn_Scene` | 0 | entry 1 = `00 01 02 00 00 03` | Scene 1 → `$07C0` |
| 3 | `EnemySpawn_Scene` | 1 | entry 2 = `00 01 02 00 00 03` | Scene 2 → `$0AC0` |
| 4 | `EnemySpawn_Scene` | 2 | entry 3 = `00 01 04 00 10 00` | Scene 3 → `$0DC0` |
| — | `EnemySpawn_Scene` | 3 | entry 4 = all zero (consumed) | guard → `loc_646` → state 7 (boss) |

The gate written at each transition is `word_195D8[Scene]` **after** the
increment (L45644-45654), so Scene 1 selects `$07C0`, not `$04C0`.
`word_195D8[0] = $04C0` is therefore never selected on this path; it must be
installed by the level-start camera setup, which was not traced here
(**UNKNOWN**, not a contradiction). The third-party note "third wave gate
`$0AC0`" lines up with Scene 2 — the transition into the third
`EnemySpawn_Scene` wave (block 3).

Evidence split:

* **`VERIFIED_DIRECT`** for the code path: palette index = `Scene+1`
  (L790-793), guard on `Scene >= 3` (L824-826), three `Init_Enemy` calls
  (L828-837), state 9 afterwards (L837), gate write in `sub_19570` (L45644-56).
* **`STRONG_INFERENCE`** for "block 2 happens at Scene 0, block 3 at Scene 1,
  block 4 at Scene 2": this follows from the fact that the level-start path
  consumes block 1 with `Scene = 0` and that `Scene` only increments when
  `$FFFA0D` is set — which the level-start path suppresses (flag 2). It is not
  observed at runtime here.
* **Cross-check:** the two documented booth positions fall in block 2
  (2016 = `$0700|$E0`) and block 3 (2920 = `$0B00|$68`), and both are reached
  *after* the corresponding gates, exactly as the wave order predicts.

### 4.2 Spawn X, verified against two runtime positions

`Init_Enemy` (L1557) builds X as `($FFFFFB12 & 0xFF00) | record_byte4`:

```
1574    move.w  ($FFFFFB12).w,d0
1577    move.b  (a2)+,d0          ; low byte replaced by the record byte
1578    move.w  d0,XPos(a1)       ; XPos equ $10 ; size - dword (high word written)
```

`Load_Enemy_Into_RAM` and `EnemySpawn_Scene` bump the base with
`add.b d2,($FFFFFB12).w` (L1828/1830/1832 and L832/834/836), i.e. the byte at
the word's address — the **high** byte. With `$FFFB20 = 1` each column therefore
adds `$0100`, and the base keeps advancing across blocks: `$0300, $0400, …,
$0E00` for twelve columns.

| Block (round 1) | Column bases | Records | Result |
| ---: | --- | ---: | --- |
| 1 | `$0300 $0400 $0500` | 6 | first wave |
| 2 | `$0600 $0700 $0800` | 10 | contains booth `$7E0` |
| 3 | `$0900 $0A00 $0B00` | 13 | contains booth `$B68` |
| 4 | `$0C00 $0D00 $0E00` | 10 | last wave |

Two independently documented runtime positions in RuiNelson's autoplay notes
(type-`$11` phone booths at world x = 2016 and x = 2920) match exactly:

* `2016 = $7E0` → block 2, byte4 `$E0` (0x0700 | 0xE0), depth 32;
* `2920 = $B68` → block 3, byte4 `$68` (0x0B00 | 0x68), depth 32.

Neither number is used as an input: the model is derived from the instructions
and the record bytes, and the two runtime values are a **held-out check**.
Class: model **VERIFIED_DIRECT**, agreement **VERIFIED_AGAINST_SECONDARY_RUNTIME**
(the runtime observation is third-party, not reproduced here).

The 1P booth list for round 1 is
`[2016, 2192, 2472, 2920, 2960, 3000, 3672]`; the 2P-only extras are at
`2072` and `3624`.

### 4.3 Why block 4 is an ordinary wave

Three independent facts rule out "block 4 is the boss pipeline":

1. The boss pipeline entry `loc_646` is reached **only after** the palette
   lookup and **before** any `Init_Enemy` call; it does not read the ELC
   cursor at all (L803-809).
2. Blocks 1–3 contain ordinary enemy types and the round-1 1P census matches
   only when **all four** blocks are counted (59 records). Dropping block 4
   would remove 10 batch/3 timed/2 deferred records and break the match.
3. Block 4's palette descriptor (`00 01 04 00 10 00`) is the only one that
   pre-loads enemy palette set 9 — the Nora/Jack set — and block 4 is the only
   block with `$26` (Nora) records. A block that were never spawned would not
   need a palette.

The remaining uncertainty is *not* "block 4 or boss" but the exact frame on
which `Scene` is observed (see §7, U1).

---

## 5. Timed and deferred records (block-local, unchanged by the above)

After the three batch columns, `EnemySpawn_Scene` sets state 9; once art is
ready the state machine reaches state 1 → 2 and `loc_784` (L945) walks the
timed list:

| Line | Instruction | Inputs | Operation | Output |
| ---: | --- | --- | --- | --- |
| L948 | `movea.l (Cur_ELC_Adr).w,a2` | cursor | — | a2 |
| L951-952 | `move.w (a2)+,d0; move.l a2,(Cur_ELC_Adr)` | delay word | consume | cursor after delay |
| L953 | `cmpi.w #$99,d0` | — | terminator? | `loc_7F0` (L994) |
| L955-967 | difficulty + 2P check | `4(a2)` low 2 bits, type bit 7 | skip? | `lea 6(a2),a2` (L968) keeps alignment |
| L973-975 | `andi.w #$7FFF,d0; move.w d0,$FFFB16` | delay | countdown | `$FFFB16` |
| L978-992 | countdown, `Find_FreeRAMSlot_Enemy`, `sub_C60` | record | spawn | object created |

`sub_C60` (L1511) uses byte 5 as edge selector (0 → `cam_x+$148`,
non-zero → `cam_x-8`) and byte 4 → object `+$15`.

After `$0099`, state 3 `EnemySpawn_Chk_Pal` reads the deferred header:

| Line | Instruction | Operation |
| ---: | --- | --- |
| L1082 | `movea.l (Cur_ELC_Adr).w,a2` | a2 = length word |
| L1083-1084 | `move.w (a2)+,d0; move.l a2,($FFFFFC2C)` | length; list start saved |
| L1085-1087 | `movea.l a2,a3; adda.w d0,a2; move.l a2,(Cur_ELC_Adr)` | cursor skipped to next block |
| L1088-1089 | `cmpi.b #$99,(a3); beq loc_910` | empty list → `loc_910` |
| L1091-1123 | palette scan of the deferred records | difficulty/2P filters |
| L1126-1149 | empty list + no live enemies → state 0, else state 6 / 4 | wave end or palette work |

`loc_B76` (L1413) spawns one deferred record through `sub_C60` and compacts
the list backwards (`move.l (a2)+,-$A(a2)`, L1434), so the list can be re-read
next frame. `$FFFFFC2C` is the list base, `$FFFFFC28` the next record.

---

## 6. Boss arrival and the tail

`loc_646` (L803) is the `Scene >= 3` destination for levels 0–3:

| Line | Instruction | Operation |
| ---: | --- | --- |
| L803-805 | `cmpi.w #6,(Level); beq loc_656` | rounds 5–7 take the other branch |
| L806 | `move.w #$E,($FFFFFB14)` | **state 7** = `loc_59C` |
| L807 | `rts` | — |

`loc_59C` (L745):

| Line | Instruction | Operation |
| ---: | --- | --- |
| L746-747 | `bset #6,($FFFFFA05).w; bne.s loc_5D4` | once per boss |
| L748 | `move.b #$E0,($FFFFF00A).w` | boss sound (`Play_SE`) |
| L749-750 | `move.w (Cam_X).w → Scene_Length / Scene_Progression` | camera span reset |
| L752 | `bsr.s sub_576` | boss palette from `$1C378[Level]` |
| L753-754 | `move.b (a3)+,d0` | **art id** from the same entry |
| L756-759 | `$FFFA63 = art id; jsr sub_8454; $FFFA4D = 1; $FFFB16 = $20` | art cue, 32-frame wait |
| L761-770 | art ready → `move.w #$12,($FFFFFB14)` (L770) | state 9 (Write_Art) |

The boss entry itself is **not** spawned here. It is spawned by the ordinary
timed runner in state 2 reading the bytes that follow block 4 — i.e. the tail.
Round 1's first tail record `56 00 04 00 10 00` is a normal record: type `$56`,
byte 5 = 0 → right edge (`cam_x + $148`), delay 16 ticks.

Full tail accounting is in `reports/stage01-boss-tail-analysis.md`.

---

## 7. Unknowns and changed hypotheses

**Changed since revision 1** (`reports/reference-stage-01.md`, commit `21cd1d8`):

| Old statement | New status | Reason |
| --- | --- | --- |
| "`EnemySpawn_Scene` refuses at `Scene >= 3` yet there are four blocks → block 4 unresolved / HYPOTHESIS" | **RESOLVED**: block 4 is the third `EnemySpawn_Scene` wave | level-start consumes block 1 at `Scene=0`; the guard counts scenes 0–2 |
| "`$FFFFFB14 = $E` consumer unknown" | **RESOLVED**: state byte `$E` = index 7 = `loc_59C` boss arrival | byte-index/word-table dispatch in `sub_436` |
| "tail framing unknown / possibly boss-specific parser" | **RESOLVED for the first section**: ordinary timed runner + deferred header | `loc_784`, `EnemySpawn_Chk_Pal` |
| "difficulty is read from `$FFFFFB5B` but `Difficulty_Copy_Byte` elsewhere" | unchanged, two copies confirmed again at L1563 and L960 | not part of this task |

**Still unknown:**

* **U1 (runtime Scene values).** The code path fixes the order, but no
  runtime observation exists here to prove that block 2 is spawned on the
  frame after `Scene` becomes 1 rather than 0. `STRONG_INFERENCE`.
* **U2 (`6a 00`).** Two bytes at `$1BE` after the round-1 deferred section are
  not read on the analysed 1P path. `Cur_ELC_Adr` (`$FFFFFC14`) has exactly
  eight references — L948/L952 and L985/L987 (state 2), L1082/L1087 (state 3),
  L1559/L1613 (`Init_Enemy`) — plus the single direct store at L1819
  (`Load_Enemy_Into_RAM`). None of them runs after the Scene ≥ 3 guard, and
  `EnemySpawn_Scene` returns before `Init_Enemy`. Meaning unknown; explicitly
  *not* forced into a record.
* **U3 (level 7 vertical wave path).** `sub_18F32` also increments `Scene`
  (L44935) and is the round-8 special case; not analysed here.
* **U4 (`$FFFA72` bit meanings).** `loc_646`/`loc_7F0` branch on bits 4 and 6
  of `$FFFFFA72`; their producers were not traced beyond `bset #6` in
  `loc_464` (L640) and `bset #0/#5` in `loc_4CA` (L665, L560).

---

## 8. Reproducibility

```bash
python3 tools/research/extract_stage01.py --listing "$SOR_LISTING"
python3 tools/research/test_stage01.py        # 14 tests, includes the
                                              # byte-accounting and census checks
```

The machine-readable form of the dispatch table is
`reports/stage01-elc-records.json` → `dispatch_model`.
