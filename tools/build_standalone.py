#!/usr/bin/env python3
"""Build a single-file, offline-playable HTML build of NEON GAUNTLET.

The result (dist/neon-gauntlet.html) contains every script, the config bundle,
the bitmap font and all PNGs (as base64 data URIs).  It runs from a file://
URL with no server, no network and no companion folder.

Usage:
    python3 tools/build_standalone.py [--out dist/neon-gauntlet.html]
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "game"
INDEX = GAME / "index.html"

SCRIPT_RE = re.compile(r'<script src="([^"]+)"></script>')


def image_paths() -> list[str]:
    """Ask the runtime itself which images it loads, so this can never drift
    from assets.js listImages()."""
    js = (
        "const {loadProject}=require('./tools/capture/harness');"
        "loadProject().then(({FD})=>{"
        "const p=FD.assets.listImages(FD.assets.data());"
        "process.stdout.write(JSON.stringify(p));});"
    )
    out = subprocess.run(
        ["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(out.stdout)


def data_uri(path: Path) -> str:
    raw = path.read_bytes()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"not a PNG: {path}")
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def inline_script(code: str, label: str) -> str:
    if "</script" in code.lower():
        # Defensive: a literal </script> inside source would close the tag early.
        code = re.sub(r"</script", r"<\\/script", code, flags=re.I)
    return f"<script>\n/* ---- {label} ---- */\n{code}\n</script>"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/neon-gauntlet.html")
    args = ap.parse_args()
    out_path = (ROOT / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = INDEX.read_text(encoding="utf-8")
    scripts = SCRIPT_RE.findall(html)
    if not scripts:
        raise SystemExit("no <script src> tags found in game/index.html")

    # ---- assets -----------------------------------------------------------
    assets: dict[str, str] = {}
    total_raw = 0
    for rel in image_paths():
        f = GAME / "assets" / rel
        if not f.exists():
            raise SystemExit(f"missing asset referenced by the game: {rel}")
        assets[rel] = data_uri(f)
        total_raw += f.stat().st_size

    embed_js = "window.FD_EMBED=" + json.dumps({"assets": assets}, separators=(",", ":")) + ";"

    # ---- replace each external script with its source ---------------------
    def repl(match: re.Match) -> str:
        src = match.group(1)
        f = (GAME / src).resolve()
        if not f.exists():
            raise SystemExit(f"missing script: {src}")
        return inline_script(f.read_text(encoding="utf-8"), src)

    out = SCRIPT_RE.sub(repl, html)

    # FD_EMBED must exist before the first module executes.
    first = out.find("<script>")
    if first < 0:
        raise SystemExit("could not place the embedded asset table")
    out = out[:first] + inline_script(embed_js, "embedded assets (FD_EMBED)") + "\n" + out[first:]

    # No external resource may remain, otherwise file:// playback breaks.
    leftovers = re.findall(r'<(?:script|link|img)[^>]+(?:src|href)="(?!#|data:)([^"]+)"', out)
    if leftovers:
        raise SystemExit(f"external references left in the build: {leftovers[:5]}")

    out_path.write_text(out, encoding="utf-8")

    size = out_path.stat().st_size
    print(f"wrote {out_path.relative_to(ROOT)}")
    print(f"  scripts : {len(scripts)} inlined")
    print(f"  images  : {len(assets)} embedded ({total_raw / 1024:.0f} KB raw)")
    print(f"  size    : {size / 1024 / 1024:.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
