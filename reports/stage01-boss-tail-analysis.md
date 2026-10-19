# Stage 1 — boss / final-wave tail across the eight rounds

Scope: the bytes that follow the last decoded wave block of each round in the
ELC stream (decoded with `tools/research/nemesis.py`, parsed with
`tools/research/elc.py`). Listing references are line numbers in
`Assemblies/Streets of Rage (JUE) (REV 00) [!].asm`.

**Summary.** In every round the tail begins with the **ordinary timed-record
grammar** (`word delay, 6-byte record` … `$0099`), and in rounds 1–6 the first
two entries are delay 16 + a type that matches the round's boss from
`$1C378`. That is the whole boss-spawn mechanism: `loc_646` (L803) only
switches palette/art, and the timed runner (`loc_784`, L945) then spawns the
boss from the cursor that the wave parser left parked on the tail. The first
section of the tail is followed by a length-prefixed section identical in
shape to a block's deferred section. Everything after that section is
**UNRESOLVED** and is reported byte-for-byte; it is *not* read on the
rounds 1–4 path because `EnemySpawn_Scene` returns at the `Scene >= 3` guard.

---

## 1. Why the tail is reached at all

| Line | Code | Effect |
| ---: | --- | --- |
| L824-826 | `cmpi.w #3,(Scene).w; bcc.s loc_646` | rounds 1–4 stop spawning wave blocks |
| L803-806 | `cmpi.w #6,(Level).w; beq.s loc_656; move.w #$E,($FFFFFB14)` | state 7 = `loc_59C` |
| L745-770 | boss palette (`sub_576`), art id, 32-frame wait, `move.w #$12,$FFFFFB14` | state 9 = `Write_Art` |
| L1633-1690 | `Write_Art` → `loc_DF4` → state 1 | camera gate, then state 2 |
| L945-952 | `loc_784: movea.l (Cur_ELC_Adr).w,a2; … move.w (a2)+,d0` | reads the **tail's first delay word** |

`Cur_ELC_Adr` (`$FFFFFC14`) is not touched between the end of the last block
and this read: the guard path returns before `Init_Enemy` (only two call
sites: L830-835 and L1826-1831), and `loc_59C` uses its own `a3` from
`off_1C378`, not the ELC cursor. So the timed runner consumes the tail with
exactly the grammar already implemented for timed records.

*Evidence class: **VERIFIED_DIRECT** for the control flow; the runtime
consequence (a boss appearing) is **STRONG_INFERENCE** because no runtime
trace was made here.*

---

## 2. The tail grammar, as observed

```
tail := pair* $0099 section leftover?
pair := word delay | 6-byte record          ; same record layout as a block
section := word length, (length-2)/6 records, $99 $00
```

Measured lengths and first pairs:

| Round | Blocks | Tail offset | Tail bytes | First pair (delay → type) | Second pair | Third pair |
| ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | 4 | `0x1A8` | 24 | 16 → `$56` (right edge) | 16 → `$D6` (left edge) | — |
| 2 | 4 | `0x256` | 42 | 16 → `$55` | 16 → `$D5` | 32 → `$22` |
| 3 | 4 | `0x1FA` | 70 | 16 → `$30` | 16 → `$B0` | 32 → `$22` |
| 4 | 4 | `0x20A` | 54 | 16 → `$57` | 16 → `$D7` | 80 → `$22` |
| 5 | 6 | `0x2F2` | 46 | 16 → `$58` | 16 → `$58` | — |
| 6 | 6 | `0x296` | 74 | 16 → `$55` | 16 → `$55` | 96 → `$A0` |
| 7 | 5 | `0x1CC` | 20 | `$FF FF FF FF FF FF` (no delay word) | — | — |
| 8 | 6 | `0x2E2` | 158 | 1 → `$33` | (framing diverges) | — |

`$8x` types are the two-player-only variants of `$0x` (`bclr #7` in
`Init_Enemy`, L1570). So round 1's pair is "Mr. X, right edge, 16 ticks, then
the 2P variant on the left edge" — the second entry is skipped in 1P by the
`PlayerMode` test, exactly like `$80`-flagged batch records.

Boss identity per round from `$1C378` (L48223-48238), read by `sub_576`
(L728): round 1 `Pal_Antonio_Blue`, 2 `Pal_Souther_Blue`, 3 `Pal_Abadede_Red`,
4 `Pal_Bongo_Blue`, 5 `Pal_Onihime_Yasha_Green`, 6 `Pal_Souther_Blue`,
7 `Pal_Abadede_Red`, 8 `word_35172` (Mr. X art). The tail type byte is not the
palette id; the correspondence listed above is a **STRONG_INFERENCE** from
"one boss per round, boss type present only in the tail, delay identical".

---

## 3. Round-by-round detail

### Round 1 (24 bytes, `0x1A8`)

```
00 10 | 56 00 04 00 10 00 | 00 10 | d6 01 05 00 10 01 | 00 99 | 00 02 | 99 00 | 6a 00
```

* pair 1: delay 16, type `$56`, byte4 `00`, byte5 `00` → `sub_C60` places it at
  `cam_x + $148`; byte4 → object `+$15`.
* pair 2: delay 16, type `$D6` (2P-only Mr. X), byte5 `01` → left edge.
* `00 99` terminates the timed list.
* `00 02` = deferred-section length 2, i.e. an **empty** deferred list
  (`99 00`), so the cursor advances past it (L1083-1087).
* `6a 00` = 2 bytes **UNRESOLVED**. They are past the end of the last section
  and are never read by any of the eight `Cur_ELC_Adr` references
  (L948/952, L985/987, L1082/1087, L1559/1613, L1819).

This closes the earlier open question about round 1: the `6a 00` bytes are
**not** a truncated record and must not be parsed as one.

### Round 2 (42 bytes)

```
pairs: 10→55, 10→d5, 20→22 ; 99 ; section 0x0E: 22 00 39 00 40 00 | 20 01 3d 00 61 01 ; 99 00
```

The whole tail is accounted for: 3 pairs (24 B) + terminator (2 B) +
length+payload (16 B) = 42 B. This is the only round whose tail parses with
**zero leftover**, which makes it the reference case for the grammar.

### Round 3 (70 bytes)

Pairs `10→30`, `10→b0`, `20→22`; section `0x14` = 3 records + `99 00`; then
22 bytes that begin like another section (`00 20` = length 32) but only 20
bytes remain. `00 20 22 00 59 00 60 01 00 99 00 14 21 00 59 00 60 01 20 01 3c 00`
contains records seen earlier in the same tail (`22 00 59 00 60 01`), so it
looks like a duplicated/looped script rather than random data. **UNRESOLVED**;
not read on the rounds 1–4 path.

### Round 4 (54 bytes)

Pairs `10→57`, `10→d7`, `50→22`; section `0x14` (20 B); 6 bytes left
(`00 50 …`). Same shape as round 3, same status.

### Round 5 (46 bytes)

Two boss pairs, both type `$58`, then terminator, then an **empty** section
(`00 02 99 00`); the remaining 20 bytes
(`40 01 a7 03 4c 00 40 00 99 00 …`) repeat record fragments. **UNRESOLVED**.

### Round 6 (74 bytes)

Two `$55` pairs (the Souther twins), then a `$A0` pair (= 2P-only `$20`) with
delay 96; section `0x14`; leftover 22 bytes of repeated records.
**UNRESOLVED**.

### Round 7 (20 bytes, `0x1CC`)

```
ff ff ff ff ff ff | 00 99 | 00 02 | 99 00 | 24 01 6b 01 69 01 26 00
```

No delay word: the tail starts with a 6-byte `$FF` group. Round 7 is the
elevator round and takes the `loc_656` branch (L810-813: `Stop_Clock`,
`End_of_Level_Flag`, state `$C`). Treating `$FF` as a record type would be
forcing unknown bytes into the record grammar — **not done**. Status
**UNRESOLVED**.

### Round 8 (158 bytes, `0x2E2`)

Starts `00 01 | 33 00 00 00 24 00` — delay 1, type `$33` — then diverges
(`15 00 00 00 80 00 … c0 00 ff ff 00 40 …`), including `$FF FF` pairs that
look like table sentinels, not delays. Round 8 is also the only round whose
*blocks* contain all earlier boss types (`$30`, `$55`, `$56`, `$57`, `$58`,
`$33`) — a boss rush before Mr. X. Status: **LOCATED / SIZE VERIFIED /
GRAMMAR UNRESOLVED**.

---

## 4. Record-count and framing checks

**Byte accounting (all eight rounds).** `walk_stream` labels every byte before
the tail; the totals close exactly, so no byte is silently dropped:

| Round | Buffer | Covered by segments | Tail | Segments sum | Closed |
| ---: | ---: | ---: | ---: | ---: | :---: |
| 1 | 448 | 424 | 24 | 424 | yes |
| 2 | 640 | 598 | 42 | 598 | yes |
| 3 | 576 | 506 | 70 | 506 | yes |
| 4 | 576 | 522 | 54 | 522 | yes |
| 5 | 800 | 754 | 46 | 754 | yes |
| 6 | 736 | 662 | 74 | 662 | yes |
| 7 | 480 | 460 | 20 | 460 | yes |
| 8 | 896 | 738 | 158 | 738 | yes |

| Claim | Check | Class |
| --- | --- | --- |
| Every round's blocks tile `[0, tail)` with no gap | `walk_stream` + `segments_cover` (tests) | VERIFIED_DIRECT |
| Tails are 24/42/70/54/46/74/20/158 bytes | test `test_tail_is_accounted_for` | VERIFIED_DIRECT |
| Tail of round 2 parses end-to-end | test `test_round2_tail_complete` | VERIFIED_DIRECT |
| First tail pair = boss entry | delay 16 appears in 6/6 informative rounds; type is unique to the tail | STRONG_INFERENCE |
| `$D5/$D6/$D7/$B0` are the 2P boss variants | `bclr #7` + PlayerMode test in `Init_Enemy` (L1568-1576) | VERIFIED_DIRECT (mechanism) |
| `6a 00` is data, not a record | eight `Cur_ELC_Adr` consumers end before it | VERIFIED_DIRECT (negative) |
| Round 7/8 tail grammar | — | UNKNOWN |

**Length prefixes and sentinels.** Two independent terminators exist and both
are used in the tails: `$0099` ends a *timed* list (tested by `cmpi.w #$99,d0`
at L953) and `$99 00` ends a *deferred* section (tested by
`cmpi.b #$99,(a3)` at L1088 and `(a2)` at L1458). A section's length word
counts its payload **including** the `99 00`; round 1's `00 02` is the
degenerate empty case.

**Origin of round 1's `6a 00`.** Candidate readings (a 107th delay, a length
word, padding, a table tail) all fail: delay `$6A` = 106 with no following
record; as a length it would need 106 bytes when only 0 remain. It is
therefore reported as unresolved data of unknown purpose, and the parser is
required to keep it in `leftover` rather than swallow it.

---

## 5. Consequences for the reconstruction

1. The boss is **not** a special record type with a separate parser: it is a
   normal 6-byte record whose type byte is looked up in the enemy/boss art
   tables and whose spawn edge comes from byte 5.
2. A faithful re-implementation needs only: block parser → timed runner →
   deferred list; the boss "phase" is palette + art + a timed entry.
3. No sprite/palette/RGB claim is made here; only indices and control flow.

## 6. Reproduction

```bash
python3 tools/research/extract_stage01.py --listing "$SOR_LISTING"
python3 tools/research/test_stage01.py
```

`reports/stage01-elc-records.json` stores, per round, `tail.offset`,
`tail.bytes`, `tail.hex` and the byte-accounting counters used above.
