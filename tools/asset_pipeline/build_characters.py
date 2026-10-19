#!/usr/bin/env python3
"""Render every animation frame, spritesheet, preview and manifest.

Source of truth for timing and hit windows: config/animation.json.
Source of truth for the look: tools/asset_pipeline/rig.py.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rig  # noqa: E402
from font5x7 import export as export_font  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "game/assets"
CONFIG = ROOT / "config"


def load_json(p):
    return json.loads(p.read_text(encoding="utf-8"))


POSERS = {
    "volt": {
        "idle": lambda i: rig.idle_pose(i, rig.LOOKS["volt"]),
        "walk": lambda i: rig.walk_pose(i, 6, rig.LOOKS["volt"]),
        "attack1": lambda i: rig.attack1_pose(i, rig.LOOKS["volt"]),
        "attack2": lambda i: rig.attack2_pose(i, rig.LOOKS["volt"]),
        "attack3": lambda i: rig.attack3_pose(i, rig.LOOKS["volt"]),
        "special": lambda i: rig.special_pose(i, rig.LOOKS["volt"]),
        "jump": lambda i: rig.jump_pose(i, rig.LOOKS["volt"]),
        "jump_attack": lambda i: rig.jump_attack_pose(i, rig.LOOKS["volt"]),
        "hurt": lambda i: rig.hurt_pose(i, rig.LOOKS["volt"]),
        "fall": lambda i: rig.fall_pose(i, rig.LOOKS["volt"]),
        "getup": lambda i: rig.getup_pose(i, rig.LOOKS["volt"]),
        "victory": lambda i: rig.victory_pose(i, rig.LOOKS["volt"]),
    },
    "rivet": {
        "idle": lambda i: rig.enemy_idle_pose(i, rig.LOOKS["rivet"]),
        "walk": lambda i: rig.enemy_walk_pose(i, rig.LOOKS["rivet"]),
        "attack": lambda i: rig.enemy_attack_pose(i, rig.LOOKS["rivet"]),
        "hurt": lambda i: rig.enemy_hurt_pose(i, rig.LOOKS["rivet"]),
        "fall": lambda i: rig.enemy_fall_pose(i, rig.LOOKS["rivet"]),
        "getup": lambda i: rig.getup_pose(i, rig.LOOKS["rivet"]),
        "defeated": lambda i: rig.enemy_defeated_pose(i, rig.LOOKS["rivet"]),
    },
}

ELITE = {"rivet": False}


def checker_bg(w, h, cell=8):
    im = Image.new("RGBA", (w, h), (16, 18, 28, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2 == 0:
                d.rectangle([x, y, x + cell - 1, y + cell - 1], fill=(24, 27, 40, 255))
    return im


def build_character(char_id: str, elite=False):
    cfg = load_json(CONFIG / "animation.json")["characters"][char_id]
    fw, fh = cfg["frame"]["width"], cfg["frame"]["height"]
    out = ASSETS / "characters" / char_id
    (out / "frames").mkdir(parents=True, exist_ok=True)
    (out / "spritesheets").mkdir(parents=True, exist_ok=True)
    (out / "previews").mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": char_id,
        "elite": elite,
        "frame": cfg["frame"],
        "source": "tools/asset_pipeline/build_characters.py",
        "animations": {},
    }
    contact_frames = []
    total = 0
    for anim, spec in cfg["animations"].items():
        poser = POSERS[char_id][anim]
        frames = []
        images = []
        for i, meta in enumerate(spec["frames"]):
            img = rig.render(char_id, poser(i), elite=elite)
            # safety: everything must stay inside the frame
            bbox = img.getbbox()
            if bbox is None:
                raise SystemExit(f"empty frame {char_id}/{anim}/{i}")
            if bbox[0] < 0 or bbox[1] < 0 or bbox[2] > fw or bbox[3] > fh:
                raise SystemExit(f"frame overflow {char_id}/{anim}/{i}: {bbox}")
            fd = out / "frames" / anim
            fd.mkdir(parents=True, exist_ok=True)
            img.save(fd / f"{anim}_{i:02d}.png")
            images.append(img)
            entry = {"i": i, "file": f"frames/{anim}/{anim}_{i:02d}.png", "dur": meta["dur"]}
            if "hit" in meta:
                entry["hit"] = meta["hit"]
            frames.append(entry)
            contact_frames.append((char_id, anim, i, img))
            total += 1
        # horizontal sheet
        sheet = Image.new("RGBA", (fw * len(images), fh), (0, 0, 0, 0))
        for i, im in enumerate(images):
            sheet.paste(im, (i * fw, 0))
        sheet.save(out / "spritesheets" / f"{anim}.png")
        # preview gif on a checker background
        gif_frames = []
        for im, meta in zip(images, spec["frames"]):
            bg = checker_bg(fw * 2, fh * 2)
            bg.alpha_composite(im.resize((fw * 2, fh * 2), Image.NEAREST))
            gif_frames.append(bg.convert("RGB"))
        gif_frames[0].save(out / "previews" / f"{anim}.gif", save_all=True,
                           append_images=gif_frames[1:],
                           duration=[int(m["dur"] * 1000 / 60) for m in spec["frames"]],
                           loop=0 if spec.get("loop") else 0, disposal=2)
        manifest["animations"][anim] = {
            "loop": bool(spec.get("loop")),
            "hold": bool(spec.get("hold")),
            "sheet": f"spritesheets/{anim}.png",
            "frames": frames,
            "totalTicks": sum(f["dur"] for f in frames),
        }
    # contact sheet with labels
    scale = 2
    cols = 8
    cell_w, cell_h = fw * scale, fh * scale + 14
    rows = math.ceil(len(contact_frames) / cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (12, 14, 22))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=11)
    except TypeError:
        font = ImageFont.load_default()
    for idx, (cid, anim, i, img) in enumerate(contact_frames):
        cx = (idx % cols) * cell_w
        cy = (idx // cols) * cell_h
        bg = checker_bg(fw * scale, fh * scale, 16)
        bg.alpha_composite(img.resize((fw * scale, fh * scale), Image.NEAREST))
        sheet.paste(bg.convert("RGB"), (cx, cy + 14))
        d.text((cx + 3, cy + 1), f"{anim} {i}", fill=(170, 230, 225), font=font)
    sheet.save(out / "previews" / "contact_sheet.png")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest, total


def main():
    export_font(ASSETS / "fonts/font5x7.json")
    manifests = {}
    count = 0
    for cid in ("volt", "rivet"):
        m, n = build_character(cid)
        manifests[cid] = m
        count += n
        print(f"{cid}: {len(m['animations'])} animations, {n} frames")
    print(f"total frames: {count}")
    print("note: the RIVET-S elite variant is a runtime tint of the rivet sheet "
          "(no duplicated files); its stats live in config/combat.json")
    print(f"total frames: {count}")


if __name__ == "__main__":
    main()
