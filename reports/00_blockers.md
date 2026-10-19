# 00 — Blockers

Each blocker states what is impossible, why, what can still be done, and what
would unblock it. Statuses are `BLOCKED` / `PARTIAL` / `RESOLVED`.

## B1 — No ROM image · BLOCKED

* **Impact:** no runtime observation, no tile/palette extraction, no sprite
  measurement, no audio capture, no ability to validate any static finding
  against the actual running game.
* **Why:** the game is copyrighted; the repository deliberately does not ship
  it and this environment must not download one.
* **Workaround in place:** all ELC work uses the `dc.b` dumps that the
  disassembly listing itself prints, so the enemy tables are decoded without
  the cartridge. Every result from this path is labelled `static`.
* **Unblocks when:** a lawful private dump is available in an environment that
  can also run an emulator. Then Gates A/C can be completed.

## B2 — No emulator or recompiled host · BLOCKED

* **Impact:** no frame-accurate captures, no camera/scroll video, no input
  traces, no proof that a spawn happens at a given frame.
* **Why:** no emulator binary, no SDL3, no CMake; `MegaDriveEnvironment` cannot
  be built, and its build would still need B1.
* **Workaround:** third-party runtime notes (RuiNelson's autoplay project) are
  used as *secondary* evidence and clearly labelled; they already confirmed two
  booth coordinates exactly.

## B3 — No interactive disassembler · PARTIAL

* **Impact:** cannot follow cross-references as quickly; cannot browse the
  `.idb` files; must rely on the exported `.asm` text and `grep`.
* **Workaround:** `tools/research/listing.py` extracts labelled `dc.b`/`dc.w`
  tables with source line numbers, so every extracted byte is traceable.
* **Residual risk:** IDA may not have emitted every data table or recognised
  every code path. Absence in the listing is not proof of absence in the game.

## B4 — Version ambiguity across sources · RESOLVED (documented)

* **Impact:** addressing a behaviour with the wrong game version silently
  produces wrong offsets.
* **Resolution:** the gsaurus listing is *Streets of Rage* JUE REV 00 (ROM
  header string `STREETS OF RAGE`); Dandaman955's Redux targets *Bare Knuckle*
  (J) (MD5 `569CFEC1…`, ROM header `BARE KNUCKLE`). Only the JUE listing is used
  for addresses. See `reports/01_target_identity.md`.

## B5 — Decompiled visuals cannot be measured · BLOCKED

* **Impact:** the style specification (Phase 3) cannot state palette values,
  sprite scale, layer composition, texture density or signage yet.
* **Workaround:** the artifact `reference-stage-01-visual-inventory.json`
  records the *addresses* where those data live (`$5F5B8` package, block maps at
  `$FF0000`/`$FF2000`, metatiles at `$FF4000`/`$FF4800`, collision map at
  `$FFA000`) and marks every measurement `BLOCKED`.
* **Unblocks with:** B1.

## B6 — Tail framing of the ELC streams · PARTIAL

* **Impact:** the boss/final-wave section of each round cannot yet be fully
  enumerated; round 1 leaves 2 unexplained bytes, round 7 has a sentinel group.
* **What is known:** the tail begins with delay/record pairs; the first type
  matches the round's boss in `$1C378` for rounds 1–6 (see
  `reference-stage-01.md` §6).
* **Next action:** trace the `$FFFFFB14 = $E` end-of-wave path and its ELC
  consumer.

## B7 — Scene-to-block mapping for waves 4+ · PARTIAL

* **Impact:** blocks 1–3 of round 1 are confirmed (two booth positions match
  runtime notes to the pixel); block 4 and its camera gate are inferred.
* **Next action:** read `sub_19646` and the pipeline table at `off_44C` to
  determine whether `Scene` is incremented before or after `EnemySpawn_Scene`.

## B8 — No baseline-runtime overlap · NOT_REQUIRED

The playable prototype in `dist/` is a separate artifact. It is not used as
evidence about the original game and must not be cited as such.
