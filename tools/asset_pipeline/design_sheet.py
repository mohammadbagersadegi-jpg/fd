#!/usr/bin/env python3
"""Compose the character design sheet: reference pose with construction guides,
palette swatches with hex codes, proportion measurements and the animation table.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rig  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/design-sheet.png"
SCALE = 5
PAD = 26
BG = (10, 12, 20, 255)
PANEL = (16, 20, 30, 255)
LINE = (34, 52, 62, 255)
CYAN = (99, 247, 255, 255)
DIM = (120, 138, 152, 255)
WHITE = (240, 244, 246, 255)
AMBER = (255, 190, 92, 255)


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def main():
    data = json.loads((ROOT / "config/animation.json").read_text())
    cfg = data["characters"]["volt"]
    frame_cfg = cfg["frame"]
    poses = {
        "IDLE": rig.idle_pose(0, rig.LOOKS["volt"]),
        "WALK": rig.walk_pose(2, 6, rig.LOOKS["volt"]),
        "ATTACK": rig.attack1_pose(1, rig.LOOKS["volt"]),
        "SPECIAL": rig.special_pose(2, rig.LOOKS["volt"]),
    }
    frames = {k: rig.render("volt", p) for k, p in poses.items()}
    fw, fh = frame_cfg["width"], frame_cfg["height"]
    cell_w, cell_h = fw * SCALE, fh * SCALE

    W = PAD * 2 + cell_w * 2 + 340
    H = PAD * 2 + cell_h * 2 + 250
    im = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((PAD, PAD), "NEON GAUNTLET / VOLT - CHARACTER DESIGN SHEET", font=font(22, True), fill=CYAN)
    d.text((PAD, PAD + 28), "original design - 16-bit inspired pixel art - all values measured from the build",
           font=font(13), fill=DIM)

    # ---- reference poses with construction guides
    names = list(frames.keys())
    for idx, name in enumerate(names):
        cx = PAD + (idx % 2) * cell_w
        cy = PAD + 66 + (idx // 2) * cell_h
        d.rectangle([cx, cy, cx + cell_w - 1, cy + cell_h - 1], fill=PANEL, outline=LINE)
        # guides: canvas box, anchor line, head-top line
        d.rectangle([cx, cy, cx + cell_w - 1, cy + cell_h - 1], outline=LINE)
        ax = cx + frame_cfg["anchorX"] * SCALE
        ay = cy + frame_cfg["anchorY"] * SCALE
        d.line([(cx, ay), (cx + cell_w, ay)], fill=(200, 80, 80, 120))
        d.line([(ax, cy), (ax, cy + cell_h)], fill=(90, 120, 200, 90))
        art = frames[name]
        scaled = art.resize((cell_w, cell_h), Image.NEAREST)
        im.alpha_composite(scaled, (cx, cy))
        d.rectangle([cx, cy, cx + cell_w - 1, cy + cell_h - 1], outline=LINE)
        d.text((cx + 8, cy + 6), name, font=font(14, True), fill=AMBER)
        d.text((cx + 8, cy + cell_h - 20), f"canvas {fw}x{fh}  anchor ({frame_cfg['anchorX']},{frame_cfg['anchorY']})",
               font=font(11), fill=DIM)

    # ---- palette column
    px = PAD + cell_w * 2 + 18
    py = PAD + 66
    d.text((px, py - 22), "PALETTE", font=font(14, True), fill=CYAN)
    pal = rig.Palette()
    entries = [
        ("jacket", pal.jacket), ("jacket dark", pal.jacket_d), ("jacket light", pal.jacket_h),
        ("inner shirt", pal.jacket_in), ("pants", pal.pants), ("pants dark", pal.pants_d),
        ("pants light", pal.pants_h), ("boot", pal.boot), ("sole", pal.sole),
        ("copper", pal.copper), ("copper dark", pal.copper_d), ("copper light", pal.copper_h),
        ("glow", pal.glow), ("glow dark", pal.glow_d), ("scarf", pal.scarf),
        ("skin", pal.skin), ("skin shadow", pal.skin_d), ("hair", pal.hair),
        ("white", pal.white), ("outline", (17, 14, 24)), ("rim light", pal.rim),
    ]
    for i, (label, col) in enumerate(entries):
        yy = py + i * 20
        d.rectangle([px, yy, px + 18, yy + 16], fill=col[:3], outline=LINE)
        d.text((px + 26, yy + 1), f"{label:14s} #{col[0]:02X}{col[1]:02X}{col[2]:02X}",
               font=font(11), fill=WHITE)
    # ---- proportions
    ty = py + len(entries) * 20 + 18
    d.text((px, ty), "PROPORTIONS (px @ 1x)", font=font(13, True), fill=CYAN)
    lines = [
        "total standing height   56 px",
        "head (hair top -> chin) 22 px  (~3.9 heads tall)",
        "shoulder width          20 px",
        "hip -> sole             27 px",
        "arm (shoulder -> wrist) 22 px",
        "leg (hip -> sole)       27 px",
        "boot length             10 px",
        "gauntlet fist            7 px",
        "ground contact = anchorY (soles overlap it by 1px)",
    ]
    for i, line in enumerate(lines):
        d.text((px, ty + 20 + i * 15), line, font=font(11), fill=DIM)

    # ---- animation table
    ay0 = PAD + 66 + cell_h * 2 + 14
    d.text((PAD, ay0), "ANIMATION SET (drives both the sprite sheets and the engine)", font=font(13, True), fill=CYAN)
    cols = ["animation", "frames", "ticks@60", "loop", "hit windows", "notes"]
    x0 = PAD
    widths = [110, 60, 74, 50, 150, 330]
    for c, w in zip(cols, widths):
        d.text((x0, ay0 + 22), c, font=font(11, True), fill=AMBER)
        x0 += w
    notes = {
        "idle": "breathing loop, gauntlet arcs every 3rd frame",
        "walk": "6 frame contact/passing cycle, 14px stride",
        "attack1": "jab, 6 active ticks",
        "attack2": "cross, 6 active ticks",
        "attack3": "roundhouse, 7 active ticks, knockdown",
        "special": "radial shock, 12 active ticks, i-frames",
        "jump": "4 frame launch/rise/fall/land",
        "jump_attack": "dive punch, 8 active ticks",
        "hurt": "2 frame flinch",
        "fall": "4 frame knockdown to floor",
        "getup": "4 frame recovery, 45 tick invulnerability",
        "victory": "4 frame loop",
    }
    y = ay0 + 40
    for anim, spec in cfg["animations"].items():
        ticks = sum(f["dur"] for f in spec["frames"])
        hits = [i for i, f in enumerate(spec["frames"]) if "hit" in f]
        row = [anim, str(len(spec["frames"])), str(ticks), "yes" if spec.get("loop") else "no",
               ",".join(map(str, hits)) if hits else "-", notes.get(anim, "")]
        x0 = PAD
        for cell, w, col in zip(row, widths, [WHITE] * 5 + [DIM]):
            d.text((x0, y), cell, font=font(11), fill=col)
            x0 += w
        y += 15

    im.convert("RGB").save(OUT)
    print(f"design sheet -> {OUT.relative_to(ROOT)} ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    main()
