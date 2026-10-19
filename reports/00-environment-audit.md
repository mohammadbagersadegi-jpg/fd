# 00 - Environment Audit

Date: 2026-10-19 (sandbox clock). Host: Linux x86_64 (Debian 12, kernel 6.1), 2 vCPU, 3.8 GB RAM, 20 GB free disk.

Everything below was executed in this sandbox and the quoted output is real. Nothing is assumed.

## 1. Dependency inventory

| Dependency | Status | Version | Evidence | Required action |
|---|---|---|---|---|
| Node.js | Installed | v22.22.3 | `node --version` | none |
| npm | Installed | 10.9.8 | `npm --version` | none |
| Python | Installed | 3.11.2 | `python3 --version` | none |
| pip (system) | Installed, PEP 668 locked | 23.0.1 | `pip install pillow` -> `error: externally-managed-environment` | use a venv |
| Python venv | Installed | 3.11 (`/tmp/venv`) | `python3 -m venv /tmp/venv` | recreated by `tools/setup.sh` |
| Pillow | Installed in venv | 13.0.0 | `python -c "import PIL; print(PIL.__version__)"` | `pip install -r requirements.txt` |
| numpy | Installed in venv | 2.4.6 | import check | same |
| imageio-ffmpeg | Installed in venv | 0.6.0 (ffmpeg 7.0.2 binary) | `imageio_ffmpeg.get_ffmpeg_exe()` | same |
| pytest | Installed in venv | 8.x | `pip install pytest` | optional |
| system ffmpeg | **Missing** | - | `command -v ffmpeg` -> not found | solved by the bundled imageio-ffmpeg binary |
| @napi-rs/canvas | Installed | 0.1.x | `npm install` + render test | `npm install` |
| Headless Chromium | **Incompatible** | @sparticuz/chromium | `/tmp/chromium: error while loading shared libraries: libnspr4.so` | not needed (see 3) |
| Playwright | **Missing** | - | pip/npm lookup | not needed |
| uv | **Missing** | - | `command -v uv` | huashu-art-motion scripts that hard-code `uv run` did not run |
| ImageMagick `convert` | Installed | 6.9.11 | `convert --version` | optional |
| Java / Ghidra / IDA Pro / Hopper | **Missing** | - | `command -v` for each | no native decompilation; text disassembly used |
| REA MCP server | **Not installed** | repo cloned, 82 MB | `git clone morluto/rea` OK; no MCP host in this environment | not used |
| OpenBOR binary | **Unavailable** | release v7533 AppImage | download failed: `curl: (35) OpenSSL SSL_connect ... release-assets.githubusercontent.com:443` | see section 4 |
| gcc / make | Installed | gcc 12.2, GNU Make 4.3 | `gcc --version` | unused |
| pkg-config / SDL2 | **Missing** | - | `command -v pkg-config` | OpenBOR cannot be built locally |
| cmake | **Missing** | - | `command -v cmake` | - |

Machine-readable copy: `reports/00-dependency-inventory.json`.

## 2. Network reachability

| Host | Reachable | Evidence |
|---|---|---|
| github.com | yes | three repositories cloned over HTTPS |
| codeload.github.com | yes | used by `git clone` |
| api.github.com | yes | `gh api repos/...` returned JSON |
| registry.npmjs.org | yes | `npm install @napi-rs/canvas` |
| pypi.org / files.pythonhosted.org | yes | `pip download imageio-ffmpeg` |
| release-assets.githubusercontent.com | **no** | `OpenSSL SSL_connect: SSL_ERROR_SYSCALL` when fetching the OpenBOR AppImage |
| apt repositories | **no** (no write access to `/var/lib/apt/lists`) | `apt-get update` -> `Permission denied` |

## 3. Rendering / verification options

The game needs a canvas to render into and screenshots for verification.

1. **Browser preview** - the build is served by `tools/serve.js` on `0.0.0.0:8080` and was smoke-tested with `curl` for HTML, JS, PNG and MP4 (200 + correct MIME). The user's browser is the display. No headless browser is required for the user.
2. **Headless Node renderer** - `@napi-rs/canvas` provides a full Canvas2D implementation in Node. `tools/capture/harness.js` loads the *same* game modules with a tiny DOM shim, so screenshots, the MP4 cinematic and the gameplay reel are rendered from production code, not a mock. This is the primary verification path in this sandbox.
3. **Headless Chromium** - abandoned: `/tmp/chromium` is missing `libnspr4`, `libnss3`, `libnssutil3` and apt is unavailable; Playwright cannot be installed. Documented as a blocked option, not a claimed success.

## 4. Engine feasibility (OpenBOR)

- `DCurrent/openbor` is alive: BSD-3-Clause, 1281 stars, tree of 593 files, latest release **v4.0 Build 7533** (2024-01-01). Assets: Android APK, Linux x64 AppImage, Linux x86 AppImage, Windows .rar.
- The AppImage **could not be downloaded** (blocked host above) and the engine **cannot be compiled** here (`cmake`, `pkg-config`, SDL2 missing, no apt).
- Consequence: an OpenBOR module could be authored but **could not be executed or verified** in this environment. Per project rule 2 ("do not claim a capability you did not test"), OpenBOR is documented as the preferred engine for a future port but is **not** the engine of the delivered build. See `reports/01-architecture-decision.md`.

## 5. Inputs

- No Streets of Rage ROM is present or was downloaded. All reverse engineering is from the public disassembly text only (see `reports/02-reverse-engineering.md`).
- Therefore no ROM hash, region or revision could be verified by hashing a file; the version is taken from the disassembly repository title and its IDA header.

## 6. Disk / time budget

- Repository + node_modules + artifacts: measured after the build; see `du -sh` output in `reports/07-final-report.md`.
- Full asset rebuild (font + 84 frames + sheets + GIF previews + 5 stage layers + props + UI): ~2 s.
- Offline video render: 12 s cinematic ≈ 10 s; 46 s gameplay reel ≈ 50 s.
