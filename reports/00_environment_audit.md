# 00 — Environment audit

**Date:** 2026-10-20 (Europe/Berlin)
**Purpose:** record exactly what this environment can and cannot do before any
reverse-engineering claim is made. Every row is tagged
`VERIFIED_AVAILABLE` / `AVAILABLE_BUT_UNTESTED` / `MISSING` / `INCOMPATIBLE` /
`BLOCKED` / `NOT_REQUIRED`.

## 1. Host

| Item | Value | Tag |
| --- | --- | --- |
| Kernel | `6.1.158+` | `VERIFIED_AVAILABLE` |
| Distribution | Debian GNU/Linux 12 (bookworm) | `VERIFIED_AVAILABLE` |
| CPU count | 2 | `VERIFIED_AVAILABLE` |
| Memory | 3 GB total, ~3 GB available | `VERIFIED_AVAILABLE` |
| Disk | 21 GB root, 19 GB free | `VERIFIED_AVAILABLE` |
| Outbound network | HTTPS to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org` only | `VERIFIED_AVAILABLE` |
| Root / `apt` | not available | `MISSING` |

## 2. Toolchain

| Tool | Version | Tag | Notes |
| --- | --- | --- | --- |
| Python | 3.11.2 | `VERIFIED_AVAILABLE` | all research tooling is stdlib-only |
| Node.js | 22.22.3 | `VERIFIED_AVAILABLE` | used for the baseline prototype's tests only |
| GCC | 12.2.0 | `VERIFIED_AVAILABLE` | never exercised for this task |
| git | available | `VERIFIED_AVAILABLE` | `--depth 1` clones |
| `gh` CLI | available | `VERIFIED_AVAILABLE` | repo/PR operations |
| CMake | — | `MISSING` | blocks building `MegaDriveEnvironment` (SDL3 host) |
| SDL3 | — | `MISSING` | same |
| FFmpeg | — | `MISSING` | blocks video encoding; not needed for RE |
| Wine | — | `MISSING` | blocks Windows binaries (IDA, emulators) |
| Java | — | `MISSING` | blocks Java-based tools |
| IDA Pro / IDA Free | — | `MISSING` | the `.idb` files in the source repos cannot be opened |
| Ghidra | — | `MISSING` | would need a JDK anyway |
| ROM image (`SOR.bin`) | — | `MISSING` | not present, not downloaded, not redistributable |
| Emulator (Genesis Plus GX, BlastEm, …) | — | `MISSING` | no binary, no SDL2/3, no build chain |
| Recompiled host (`sor`) | — | `BLOCKED` | requires CMake + SDL3 + the ROM to generate C++ |

Checked with `command -v` on 2026-10-20: `cmake`, `ffmpeg`, `wine`, `java`,
`ida`, `ghidra` all absent.

## 3. What this means for the project

* **Runtime observation of the original game: BLOCKED.** No ROM, no emulator,
  no recompiled host. Any statement about on-screen behaviour must be labelled
  as static analysis, inference, or *someone else's* documented runtime result.
* **Static analysis of the disassembly: AVAILABLE.** The text listing
  (`gsaurus/sor-disassemblies`) contains the code and the `dc.b`/`dc.w` data
  tables. Data tables can be extracted and decompressed without the ROM.
* **Reading the IDA database: BLOCKED.** Only the exported `.asm` is usable.
* **Building the recompilation: BLOCKED.** Missing CMake/SDL3 *and* the ROM.
* **Emulator-based capture: BLOCKED.** No emulator binary and no ROM.
* **Screenshot/visual measurement of the original art: BLOCKED.** Requires the
  cartridge art to be decoded (or a running game); neither is possible here.
* **Phase 1 structure work: AVAILABLE and already producing verified results**
  (see `reports/reference-stage-01.md`).

## 4. Honesty constraints that follow

1. No claim of "tested in game", "verified in emulator" or "matches the ROM in
   motion" is permitted.
2. Third-party runtime notes (RuiNelson's recompiled runs) may be used only as
   **secondary evidence** and must be labelled as such.
3. Visual-style measurements that need the art cannot be invented; they stay
   `BLOCKED` until a lawful ROM dump is available in an environment that can
   decode it.
4. The baseline playable prototype (`dist/neon-gauntlet.html`) is a separate
   artifact and is **not** evidence about the original game.
