# Stage 1 — palette and scene descriptors (indices only)

**No colour data is interpreted.** This note records the palette *selection*
machinery: table addresses, entry sizes, which entry is used for which wave,
and how the selector byte is consumed. RGB words exist in the listing and are
deliberately not converted; a colour claim would need a rendering path this
environment does not have.

Listing references are line numbers in
`Assemblies/Streets of Rage (JUE) (REV 00) [!].asm`.

---

## 1. The two-level table

| Address | Line | Contents |
| --- | ---: | --- |
| `word_1C1BC` | 48087 | geometry words: `(1, $0300)`, `($FFFF, $1300)` |
| `off_1C1C4` | 48089 | 8 words: per-round relative offsets to that round's descriptor table |
| `off_1C1D4` … `off_1C33A` | 48098-48206 | the eight per-round tables |
| `off_1C378` | 48223 | 8 boss art/palette entries (read by `sub_576`, L728) |
| `Pal_Alt_Boss` | 48239 | boss palette *lists* (read by `Update_Enemy_Pal`) |
| `Pal_Alt_Enemy` | 49071 | 12 relative words, enemy palette pairs |

The per-round lookup is used twice:

1. **Level start** — `Load_Enemy_Into_RAM` (L1779) reads slot `Scene` (= 0),
   takes a 4-byte ELC cursor, a 2-byte geometry index and then a 6-byte
   descriptor.
2. **Every wave transition** — `EnemySpawn_Scene` (L777) reads slot
   `Scene + 1` (L790-793) and consumes only the 6-byte descriptor.

Because slot 0 also embeds the cursor and geometry, slot 0 is 12 bytes of
data while slots 1..n are 6 bytes each. The offset list length is
`word(root)/2`, which the extractor uses instead of guessing from neighbour
addresses.

---

## 2. Table sizes match the scene guards

| Round | Root | Slots | Table bytes | Scene guard | Decoded blocks |
| ---: | --- | ---: | ---: | --- | ---: |
| 1 | `off_1C1D4` | 5 | 46 | `Scene >= 3` (L825) | 4 |
| 2 | `off_1C202` | 5 | 46 | `Scene >= 3` | 4 |
| 3 | `off_1C230` | 5 | 46 | `Scene >= 3` | 4 |
| 4 | `off_1C25E` | 5 | 46 | `Scene >= 3` | 4 |
| 5 | `off_1C28C` | 7 | 62 | `Scene >= 5` (L800) | 6 |
| 6 | `off_1C2CA` | 7 | 62 | `Scene >= 5` | 6 |
| 7 | `off_1C308` | 7 | 50 | `Scene >= 5`, `loc_66A` | 5 + tail |
| 8 | `off_1C33A` | 7 | 62 | level-specific | 6 |

`slots = guard_scene + 2` in every case: one slot for level start, one for
each spawned wave, one for the guard frame that is still consumed. This is an
independent consistency check on the decoded block counts — the table was not
read to derive the counts, and the counts were not used to size the table.

*Class: **VERIFIED_DIRECT** (offsets and byte sizes read from `dc.w` data);
the guard mapping for round 7/8 is **STRONG_INFERENCE** because `loc_66A`
adds a second branch.*

---

## 3. What a descriptor means

`Update_Enemy_Pal` (L1865) consumes a descriptor as follows:

| Bytes | Destination | Meaning (as used) |
| --- | --- | --- |
| 0-3 | `$FFFFFA60..$FFFFFA63` (`Pal_Correct`) | palette-correctness bookkeeping |
| 4 | `d0` → selector | bit 7 = boss table; high nibble + 8 = `Pal_ID_Enemy`; low nibble tested |
| 5 | `$FFFFFA6A` (low nibble) | palette-variant / "alternate" selector |

The 6-byte spacing is fixed by the offset table; all six bytes are read (byte 5
as the low half of the `move.w (a1),$FFFFFA6A`), and `a1` finishes pointing at
byte 5 because no caller advances it further.

Round 1 example (`00 01 02 00 00 03`): low nibble of byte 4 is 0, so the
enemy path is taken with palette index 0. Round 1 slot 3
(`00 01 04 00 10 00`): byte 4 = `$10` → `+8` → `Pal_ID_Enemy = 9`, i.e. the
Nora/Jack palette set. That slot is used for the **fourth** wave, which is the
only round-1 block containing type `$26` (Nora) — a cross-check between the
descriptor table and the decoded records.

The boss branch (`bit 7` of byte 4, L1881-1889) indexes `Pal_Alt_Boss`: `d0 = (byte4 & $7F)`, `offset = d0 * 6`, load the long at
`Pal_Alt_Boss + offset + 2`, then a list of palette pointers. The 6-byte boss
entries are `(descriptor_word, long palette_list)`:

| Index | Descriptor word | Palette list |
| ---: | ---: | --- |
| 0 | `$551B` | `off_1C3CC` (Souther ×3) |
| 1 | `$561C` | `off_1C3D8` (Antonio ×2) |
| 2 | `$571D` | `off_1C3E0` (Bongo ×3) |
| 3 | `$581E` | `off_1C3EC` (Onihime/Yasha ×2) |
| 4 | `$3008` | `off_1C3F4` (Abadede ×3) |
| 5 | `$3505` | `word_35172` (single palette, not a list) |

The descriptor words are opaque here: they are not RGB and are not interpreted.

---

## 4. Per-round descriptor bytes

Extracted by `tools/research/stage01_tables.py`; full JSON in
`reports/stage01-palette-descriptors.json`. `slot 0` shows cursor / geometry /
descriptor; later slots are descriptor only.

| Round | slot 0 | 1 | 2 | 3 | 4 | 5 | 6 |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `$FF6800` / geom 0 / `00 01 02 00 00 03` | `00 01 02 00 00 03` | `00 01 03 00 00 06` | `00 01 04 00 10 00` | `00 00 00 00 00 00` | — | — |
| 2 | `$FF6800` / 0 / `00 01 02 00 00 03` | `01 04 00 00 10 00` | `01 03 00 00 00 06` | `01 03 05 00 10 06` | `01 00 00 00 00 00` | — | — |
| 3 | `$FF6800` / 0 / `01 03 00 00 01 06` | `01 04 05 00 11 00` | `02 03 04 00 13 06` | `01 04 05 00 11 00` | `01 00 00 00 00 00` | — | — |
| 4 | `$FF6800` / 0 / `01 02 04 00 21 04` | `01 02 00 00 01 04` | `03 02 04 00 27 03` | `01 02 00 00 01 04` | `01 00 00 00 00 01` | — | — |
| 5 | `$FF6800` / 0 / `01 02 00 00 00 01` | `01 03 00 00 01 07` | `02 04 00 00 23 00` | `01 03 00 00 01 06` | `03 05 00 00 26 00` | `01 02 00 00 01 04` | `00 00 00 00 00 00` |
| 6 | `$FF6800` / 0 / `01 02 00 00 02 04` | `01 02 00 00 02 04` | `01 03 00 00 02 07` | `01 02 04 00 22 04` | `03 04 05 00 27 02` | `02 03 05 00 24 07` | `01 00 00 00 00 00` |
| 7 | `$FF6800` / 0 / `01 03 00 00 01 06` | *alias of slot 0* | `01 03 00 00 01 06` | `03 02 00 00 07 03` | `03 02 04 00 27 04` | `03 02 04 00 17 03` | *alias of slot 5* |
| 8 | `$FF6800` / **geom 4** / `01 02 04 00 10 03` | `01 02 05 00 11 04` | `01 02 05 00 22 04` | `02 05 00 00 24 05` | `03 04 00 00 27 08` | `03 04 05 00 38 05` | `00 01 00 05 00 02` |

Observations that follow from the bytes, not from interpretation:

* Every round pins the same ELC buffer (`$FF6800`, i.e. `Cur_ELC_Adr`'s
  initial value).
* Geometry is 0 for rounds 1–7; round 8 selects geometry 4 — **outside the
  two-entry table** `word_1C1BC`. That is a genuine anomaly: either the table
  is longer than the listing shows here, or round 8 takes a different path.
  Flagged **UNKNOWN**, not smoothed over.
* Rounds 1–4 end their descriptor list with an all-zero or `01 00 …` entry;
  the guard frame consumes it (L793) before the guard test (L825).
* Round 7's slots 1 and 6 are *aliases* of slots 0 and 5 (the same offset word
  appears twice), so its "5 spawns" reading is softer than the others.

---

## 5. What is *not* claimed

* No RGB, no colour names, no palette-line assignment beyond the index
  arithmetic above.
* No claim that identity mapping "type → palette" is complete: `sub_A66`
  (L1301) further offsets the palette by record byte 3 and by `Pal_Count`
  bookkeeping; that path is only partially traced.
* `Pal_Alt_Enemy`'s 12 relative words are located and sized but their contents
  were not extracted; `reports/stage01-palette-descriptors.json` records them
  as `UNKNOWN` rather than as zeros.

## 6. Reproduction

```bash
python3 tools/research/stage01_tables.py --listing "$SOR_LISTING"
```

The script evaluates only `dc.b/dc.w/dc.l` inside three labelled regions and
stores the raw bytes alongside every derived index, so each number above can
be traced back to a listing line.
