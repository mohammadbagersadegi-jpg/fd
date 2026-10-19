# 00 — Repository map

What each reference source actually contains, and what it can be used for
here. Clones are shallow (`--depth 1`) and live outside the repo so that no
third-party code or data is redistributed.

## 1. `RuiNelson/StreetsOfRageProject` — meta-repository

* commit `d91bea9`, 2026-10-18, 11 MB, **no top-level license file**.
* Contains `README.md`, `docs/`, `scripts/`, and empty submodule directories
  (`MegaDriveEnvironment/`, `RageDecompiler/`, `StreetsOfRageRecompilation/`,
  `autoplay/`, `MegaDriveEnvironmentSampleGame/`) because of the shallow clone.
* **Usable:** `README.md` — roadmap, recompiler design, and the authoritative
  JUE cartridge hashes (size 524 288, CRC32 `4052E845`,
  MD5 `59a3b22a1899461dceba50d1ade88d3a`,
  SHA-256 `95d7efb98e97f4ffffe68257aef9a855034a36a41b86cf9d332d129f30cb2d4b`).
* **Not usable:** the empty submodules — clone those individually.
* Status: `VERIFIED_AVAILABLE`.

## 2. `RuiNelson/StreetsOfRageRecompilation`

* commit `64c7442`, 2026-10-18, 1.4 MB, **MIT**.
* `ai-analysis/` — long-form prose analyses with ROM addresses: stage/level
  engine, enemy AI, rendering, audio. These are the richest offline
  descriptions of the game's data structures.
* `code-analysis/*.csv` — label/address tables.
* `tools/decompress.py` — independent Nemesis decoder (MIT).
* `rom/` — contains only `.gitignore`; **no ROM**.
* **Usable:** everything except the ROM. Confirms ELC framing, the camera
  model, RAM map, compression families.
* Status: `VERIFIED_AVAILABLE`.

## 3. `gsaurus/sor-disassemblies`

* commit `4dd719f`, 2020-05-09, 137 MB, **no license file**.
* `Assemblies/Streets of Rage (JUE) (REV 00) [!].asm` — 72 920 lines, IDA
  export with symbol names, comments and `dc.b`/`dc.w` data dumps. SHA-256
  `b21835df76ba33bc11c0d922bada8947d19106c8f112b61d8715abab4704ac16`.
* `.idb` database files — **cannot be opened** (no IDA).
* **Usable:** the entire text listing, which is the primary source for every
  claim in this phase. Because the listing prints the data bytes, the ELC
  streams can be decoded without the ROM.
* **Caveat:** an IDA listing is a partial view. Data only appears where IDA
  emitted it; code paths that the disassembler missed, or data reached by
  runtime pointers, may be absent.
* Status: `VERIFIED_AVAILABLE` (text) / `INCOMPATIBLE` (`.idb`).

## 4. `Dandaman955/Streets-of-Rage-1-Disassembly-Redux`

* commit `e09451e`, 2015-12-27, 3.1 MB, **no license file**.
* `SoR.asm` header: input MD5 `569CFEC15813294A8F0CF88CCCC8C151`,
  CRC32 `BFF227C6`; the ROM header string is `BARE KNUCKLE`.
* Currently the file is a partial rebuild ("old one is trapped/gone on a broken
  HDD, so I'm starting again").
* Status: `INCOMPATIBLE` — this is the Japanese release. **Do not** copy
  addresses, tables or byte offsets from it into work based on the JUE
  listing. Useful only as a second opinion on *concepts*, never on addresses.

## 5. `morluto/rea`

* commit `7a0c47b`, 2026-10-19, MIT.
* An MCP-style wrapper for reverse-engineering agents.
* Status: `AVAILABLE_BUT_UNTESTED` — no MCP host exists in this environment, so
  it was not used and no claim depends on it.

## 6. `alchaincyf/huashu-art-motion`

* commit `8a0d7d7`, 2026-10-17, MIT.
* Video-generation workflow; outputs short video shots, not sprite sheets.
* Status: `NOT_REQUIRED` for Phase 0–1. Deferred to Phase 5 and gated by the
  directive; it may be evaluated for animatics only.

## 7. What is not available at all

| Missing | Consequence |
| --- | --- |
| Streets of Rage (JUE) ROM | no runtime, no art decode, no palette extraction |
| Emulator binary | no frame capture, no input/output observation |
| CMake + SDL3 | cannot build the recompiled host even with a ROM |
| IDA / Ghidra | cannot re-open the disassembly interactively |

These are recorded again, with impact and workarounds, in
`reports/00_blockers.md`.
