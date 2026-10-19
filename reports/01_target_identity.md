# 01 — Target identity

Which game exactly this research describes, and why the answer is not optional.

## 1. Identity used throughout

| Property | Value | Evidence |
| --- | --- | --- |
| Title | *Streets of Rage* (export / "JUE" release) | ROM header string in the listing: `STREETS OF RAGE` |
| Region build | JUE (Japan–USA–Europe), REV 00 | repository/file name of the gsaurus listing (`(JUE) (REV 00) [!]`) |
| Size | 524 288 bytes (512 KiB) | `RuiNelson/StreetsOfRageProject` README |
| CRC32 | `4052E845` | same README |
| MD5 | `59a3b22a1899461dceba50d1ade88d3a` | same README |
| SHA-256 | `95d7efb98e97f4ffffe68257aef9a855034a36a41b86cf9d332d129f30cb2d4b` | same README |
| Disassembly used | `Assemblies/Streets of Rage (JUE) (REV 00) [!].asm`, 72 920 lines | gsaurus/sor-disassemblies, commit `4dd719f` |
| Listing SHA-256 | `b21835df76ba33bc11c0d922bada8947d19106c8f112b61d8715abab4704ac16` | computed here |

`VERIFIED_AVAILABLE` for the hashes (published) and for the listing text;
`MISSING` for the ROM itself. **No hash of our own was ever computed**, because
no ROM exists in this environment. Do not claim otherwise.

## 2. The conflicting second disassembly

`Dandaman955/Streets-of-Rage-1-Disassembly-Redux` is **not** the same game
build:

| Property | Redux value | Evidence |
| --- | --- | --- |
| Input MD5 | `569CFEC15813294A8F0CF88CCCC8C151` | header of `SoR.asm` |
| Input CRC32 | `BFF227C6` | header of `SoR.asm` |
| ROM header string | `BARE KNUCKLE` | `dc.b 'SEGA MEGA DRIVE (C)SEGA 1991.MAYBARE KNUCKLE'` |
| Date stamp | 2015-12-27, partial rebuild | repository commit + README |

Consequences:

* Addresses, table offsets and byte layouts **must not be cross-referenced**
  between the two disassemblies. A matching-looking offset is a coincidence.
* The Redux may still be useful for *concepts* (how a routine is shaped, what a
  structure means) — never for numeric values.
* Any future report must state which build a claim comes from.

## 3. Other builds that must not be confused with this target

| Source | Build | Status |
| --- | --- | --- |
| `RuiNelson/StreetsOfRageProject` + `...Recompilation` | JUE, same hashes as above | `VERIFIED_AVAILABLE` (different toolchain, same game) |
| `gsaurus/sor-disassemblies` | JUE REV 00 | `VERIFIED_AVAILABLE` |
| `Dandaman955/...Redux` | Bare Knuckle (J) | `INCOMPATIBLE` for addresses |
| `DCurrent/openbor` | engine, not the game | `NOT_REQUIRED` |

## 4. Practical rules

1. Cite the listing **filename and line number** with every static fact.
2. When quoting the recompilation analysis, cite the document and section.
3. When quoting autoplay runtime notes, mark them
   `VERIFIED_AGAINST_SECONDARY_RUNTIME` — they are RuiNelson's observations,
   not ours.
4. Never mix a Bare Knuckle address into a JUE claim.
5. If a future ROM dump is used, record its SHA-256 and compare against the
   table above **before** trusting any address.
