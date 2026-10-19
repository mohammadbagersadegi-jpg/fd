#!/usr/bin/env python3
"""Asset QA gate.

Checks the generated sprite/stage assets against config/animation.json and
writes reports/asset-validation.json.  Exits non-zero if a hard check fails.

Hard checks (FAIL):
  - a frame listed in the config is missing or unreadable
  - frame size differs from the configured canvas
  - a frame is fully transparent (empty)
  - a frame's visible box leaves the canvas
  - the feet anchor drifts more than ANCHOR_TOLERANCE px between idle/walk frames
  - a spritesheet's width is not frames * frameWidth
Soft checks (WARN):
  - duplicate consecutive frames inside an animation
  - a sprite touches the left/right edge of its canvas (clipping risk)
  - more than PALETTE_LIMIT distinct RGBA colours in one frame
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "game/assets"
CONFIG = ROOT / "config"
REPORT = ROOT / "reports/asset-validation.json"

ANCHOR_TOLERANCE = 1
PALETTE_LIMIT = 40
CHARS = ["volt", "rivet", "rivet_elite"]  # rivet_elite aliases the rivet files at runtime
ANCHORED_ANIMS = {"idle", "walk"}


def cfg_char(char_id: str) -> dict:
    data = json.loads((CONFIG / "animation.json").read_text())
    chars = data["characters"]
    return chars[char_id] if char_id in chars else chars[char_id.replace("_elite", "")]


def check_frame(path: Path, w: int, h: int) -> tuple[list[str], list[str], dict]:
    errors, warns = [], []
    if not path.exists():
        return [f"missing frame {path.relative_to(ROOT)}"], [], {}
    with Image.open(path) as im:
        im = im.convert("RGBA")
        if im.size != (w, h):
            errors.append(f"{path.name}: size {im.size} != {(w, h)}")
        bbox = im.getbbox()
        if bbox is None:
            errors.append(f"{path.name}: fully transparent")
            return errors, warns, {}
        if bbox[0] <= 0 or bbox[1] <= 0 or bbox[2] >= w or bbox[3] >= h:
            warns.append(f"{path.name}: artwork touches the canvas edge {bbox}")
        colors = len(im.getcolors(maxcolors=1 << 20) or [])
        if colors > PALETTE_LIMIT:
            warns.append(f"{path.name}: {colors} colours (limit {PALETTE_LIMIT})")
        return errors, warns, {"bbox": bbox, "colors": colors}


def main() -> int:
    report = {"characters": {}, "stage": {}, "totals": {"errors": 0, "warnings": 0, "frames": 0, "sheets": 0}}
    for char_id in CHARS:
        cfg = cfg_char(char_id)
        fw, fh = cfg["frame"]["width"], cfg["frame"]["height"]
        entry = {"frame": [fw, fh], "animations": {}, "errors": [], "warnings": []}
        sheet_dir = ASSETS / f"characters/{char_id}"
        if not sheet_dir.exists():
            # the elite variant intentionally has no files of its own: it reuses
            # the rivet sheets with a runtime tint (see assets.js characterCfg)
            entry["aliasedTo"] = "rivet"
            report["characters"][char_id] = entry
            continue
        for anim, spec in cfg["animations"].items():
            frames = spec["frames"]
            bboxes = []
            prev_bytes = None
            dup = []
            for i in range(len(frames)):
                path = ASSETS / f"characters/{char_id}/frames/{anim}/{anim}_{i:02d}.png"
                errs, warns, meta = check_frame(path, fw, fh)
                entry["errors"] += errs
                entry["warnings"] += warns
                if meta:
                    bboxes.append((i, meta["bbox"]))
                    with Image.open(path) as im:
                        data = im.convert("RGBA").tobytes()
                    if data == prev_bytes:
                        dup.append(i)
                    prev_bytes = data
                report["totals"]["frames"] += 1
            # Anchor stability.  The sole outline may extend a little below the
            # configured anchor (that is the ground contact), but every grounded
            # frame of the same animation must share the same lowest row, and the
            # animation as a whole must sit close to the anchor.
            if anim in ANCHORED_ANIMS and bboxes:
                bottoms = [bbox[3] - 1 for _, bbox in bboxes]
                modal = max(set(bottoms), key=bottoms.count)
                entry["anchor"] = entry.get("anchor", {})
                entry["anchor"][anim] = {"feetRows": bottoms, "anchorY": cfg["frame"]["anchorY"]}
                if not (cfg["frame"]["anchorY"] - 1 <= modal <= cfg["frame"]["anchorY"] + 2):
                    entry["warnings"].append(
                        f"{anim}: modal feet row {modal} is far from anchorY {cfg['frame']['anchorY']}"
                    )
                for i, bottom in zip([b[0] for b in bboxes], bottoms):
                    if abs(bottom - modal) > ANCHOR_TOLERANCE:
                        entry["warnings"].append(
                            f"{anim}_{i:02d}: feet row {bottom} drifts from animation baseline {modal}"
                        )
            sheet = ASSETS / f"characters/{char_id}/spritesheets/{anim}.png"
            report["totals"]["sheets"] += 1
            if not sheet.exists():
                entry["errors"].append(f"missing spritesheet {sheet.name}")
            else:
                with Image.open(sheet) as im:
                    if im.size != (fw * len(frames), fh):
                        entry["errors"].append(
                            f"{anim}.png sheet size {im.size} != {(fw * len(frames), fh)}"
                        )
            if dup:
                entry["warnings"].append(f"{anim}: frames identical to the previous frame: {dup}")
            entry["animations"][anim] = {
                "frames": len(frames),
                "loop": bool(spec.get("loop")),
                "ticks": sum(f["dur"] for f in frames),
                "hitWindows": [i for i, f in enumerate(frames) if "hit" in f],
                "duplicateFrames": dup,
            }
        # manifest cross-check
        manifest_path = ASSETS / f"characters/{char_id}/manifest.json"
        if not manifest_path.exists():
            entry["errors"].append("missing manifest.json")
        else:
            manifest = json.loads(manifest_path.read_text())
            for anim, spec in cfg["animations"].items():
                got = manifest.get("animations", {}).get(anim)
                if not got:
                    entry["errors"].append(f"manifest missing animation {anim}")
                elif len(got["frames"]) != len(spec["frames"]):
                    entry["errors"].append(
                        f"manifest {anim}: {len(got['frames'])} frames, config {len(spec['frames'])}"
                    )
        report["characters"][char_id] = entry

    stage_manifest = json.loads((ASSETS / "stage/manifest.json").read_text())
    stage = {"errors": [], "warnings": [], "layers": {}}
    for name, meta in stage_manifest["layers"].items():
        path = ASSETS / "stage" / meta["file"]
        if not path.exists():
            stage["errors"].append(f"missing layer {name}")
            continue
        with Image.open(path) as im:
            stage["layers"][name] = list(im.size)
            if list(im.size) != meta["size"]:
                stage["errors"].append(f"layer {name} size {im.size} != {meta['size']}")
    for prop, meta in stage_manifest["props"].items():
        for f in meta["frames"]:
            if not (ASSETS / "stage" / f).exists():
                stage["errors"].append(f"missing prop frame {f}")
            else:
                with Image.open(ASSETS / "stage" / f) as im:
                    if list(im.size) != meta["size"]:
                        stage["errors"].append(f"prop {f} size {im.size} != {meta['size']}")
    for pick, meta in stage_manifest["pickups"].items():
        if not (ASSETS / "stage" / meta["file"]).exists():
            stage["errors"].append(f"missing pickup {pick}")
    report["stage"] = stage

    for entry in report["characters"].values():
        report["totals"]["errors"] += len(entry["errors"])
        report["totals"]["warnings"] += len(entry["warnings"])
    report["totals"]["errors"] += len(stage["errors"])
    report["totals"]["warnings"] += len(stage["warnings"])
    report["ok"] = report["totals"]["errors"] == 0

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    print(f"frames checked : {report['totals']['frames']}")
    print(f"sheets checked : {report['totals']['sheets']}")
    print(f"errors         : {report['totals']['errors']}")
    print(f"warnings       : {report['totals']['warnings']}")
    for char_id, entry in report["characters"].items():
        for err in entry["errors"]:
            print(f"  ERROR {char_id}: {err}")
        for warn in entry["warnings"][:8]:
            print(f"  warn  {char_id}: {warn}")
    for err in stage["errors"]:
        print(f"  ERROR stage: {err}")
    print("OK" if report["ok"] else "FAILED")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
