# 01 - Engine Comparison

Scoring is based on what was *actually* verified in this sandbox on 2026-10-19.
`Y` = verified available, `N` = verified unavailable, `?` = not verifiable here.

| Criterion | OpenBOR (v7533) | SoRMaker (SoR Remake) | This project's browser engine |
|---|---|---|---|
| Engine obtainable here | **N** - AppImage download blocked | **N** - no public source/tool, not in environment | Y - plain JS + Canvas2D |
| Engine buildable here | **N** - cmake/pkg-config/SDL2 missing | N | Y - no build step |
| Executable/verifiable in this sandbox | **N** | N | **Y** - headless Node renderer + HTTP preview |
| New playable character | Y (documented feature) | ? (version-dependent, undocumented here) | Y - implemented and tested |
| Custom sprite animations | Y (texture libraries) | ? | Y - 12 animations for the hero |
| Hit/hurt boxes | Y (attack boxes) | ? | Y - per-frame rectangles in JSON |
| New stage | Y | ? | Y - 1800 px segment + 3 waves |
| Custom enemies / AI | Y (scripted) | ? | Y - RIVET + RIVET-S archetypes |
| Special moves | Y | ? | Y - radial electric special |
| Standalone output | Y (engine + .pak) | Y (patched exe) | Y (static site) |
| Documentation quality | good (engine repo + community) | low / fragmented | in-repo docs, this report set |
| Setup cost | high (module format, packer) | high (proprietary tooling) | low |
| Automated testing | **N** (manual play) | **N** | **Y** - 23 automated checks |
| Original art usable | Y | ? | Y - all art generated here |
| Long-term maintainability | strong (community) | weak | strong (plain ES2020 + JSON) |

## What actually happened with each candidate

**OpenBOR.** The repository exists, is BSD-3-Clause and actively released (v4.0 Build 7533, 2024-01-01). Two independent blockers were confirmed: (1) the release asset host is unreachable from this sandbox (`curl: (35) OpenSSL SSL_connect ... release-assets.githubusercontent.com:443`), and (2) the engine cannot be compiled here because `cmake`, `pkg-config` and SDL2 are absent and apt is read-only. Writing a `models.txt`/`animationscript` module without being able to launch it would violate the "no untested claims" rule, so OpenBOR was **not** chosen for the delivered build.

**SoRMaker / Streets of Rage Remake.** No source, tool or binary exists in this environment, and the project is a closed binary distribution whose modding API varies by build. Nothing could be verified, so the route was rejected on evidence, not on preference.

**Browser engine (chosen).** It is the only path that satisfies all three constraints that mattered: original assets, fully controllable feel, and *verifiable execution* in this sandbox. It also keeps the whole vertical slice inspectable: config → sprites → engine → tests → video, all in one repository.

The comparison above is why the delivered game is not an OpenBOR module. That is a deliberate, evidence-based decision, not an omission. A future OpenBOR port is scoped in `reports/07-final-report.md` §remaining work: the config-driven data model maps 1:1 onto OpenBOR's model/attack-box concepts, so the port is a translation task, not a redesign.
