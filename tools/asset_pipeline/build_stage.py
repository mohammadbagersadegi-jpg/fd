#!/usr/bin/env python3
"""Build the original RAIN DISTRICT stage layers, props, pickups and UI art.

Art direction: original 16-bit-inspired pixel art.  Deep indigo night, wet
asphalt reflecting cyan/magenta neon, copper sodium lamps.  All shapes are
authored here; nothing is sampled from a commercial game.

Layers (parallax factor in brackets):
    sky.png   480x270 [0.00]  gradient + haze + distant glow
    far.png   512x270 [0.15]  tileable skyline silhouettes
    mid.png   960x270 [0.45]  tileable building facades, neon signs
    near.png  1800x270 [1.00] unique street surface for the whole segment
    fg.png    480x270 [1.18]  tileable foreground railings / lamps
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rig  # noqa: E402
from font5x7 import G as FONT  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "game/assets/stage"
W, H = 480, 270
LANE_MIN, LANE_MAX = 204, 250
GROUND_Y = 244

SKY = [(9, 10, 24), (13, 15, 36), (22, 20, 52), (34, 26, 62), (44, 30, 66)]
FAR = (18, 20, 44)
FAR_LIGHT = (30, 34, 66)
MID_DARK = (26, 24, 46)
MID_DARK2 = (34, 30, 56)
NEON_C = (86, 240, 255)
NEON_M = (255, 92, 190)
NEON_A = (255, 178, 74)
NEON_G = (120, 255, 168)
WINDOW = (255, 206, 120)
WINDOW_C = (150, 226, 240)
ASPHALT = (24, 24, 36)
ASPHALT_HI = (34, 35, 52)
SIDEWALK = (40, 40, 56)
SIDEWALK_HI = (52, 53, 70)
CURB = (62, 62, 78)


def img(w, h, rgba=(0, 0, 0, 0)):
    return Image.new("RGBA", (w, h), rgba)


def vertical_gradient(w, h, stops):
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        pos = t * (len(stops) - 1)
        i = min(len(stops) - 2, int(pos))
        f = pos - i
        c0, c1 = stops[i], stops[i + 1]
        col = tuple(int(c0[k] + (c1[k] - c0[k]) * f) for k in range(3)) + (255,)
        d.line([(0, y), (w, y)], fill=col)
    return im


def glow_layer(base: Image.Image, draw_fn, blur=7, gain=1.0):
    """Draw a neon shape on its own layer, blur it and add it to ``base``."""
    layer = img(base.width, base.height)
    d = ImageDraw.Draw(layer)
    draw_fn(d)
    halo = layer.filter(ImageFilter.GaussianBlur(blur))
    halo = halo.point(lambda v: min(255, int(v * gain)))
    out = base.copy()
    out.alpha_composite(halo)
    out.alpha_composite(layer)
    return out


def dither(im, rect, amount=10, seed=7):
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)
    x0, y0, x1, y1 = rect
    for y in range(y0, y1):
        for x in range(x0, x1):
            if rnd.random() < 0.06:
                px = im.getpixel((x, y))
                f = 1 + rnd.uniform(-amount, amount) / 100
                d.point((x, y), fill=tuple(max(0, min(255, int(c * f))) for c in px[:3]) + (px[3],))
    return im


# ---------------------------------------------------------------------------
# sky
# ---------------------------------------------------------------------------
def build_sky():
    im = vertical_gradient(W, H, SKY)
    d = ImageDraw.Draw(im)
    # city glow near the horizon
    for y in range(150, 200):
        f = (y - 150) / 50
        col = (int(28 + 26 * f), int(20 + 14 * f), int(46 + 30 * f), 255)
        d.line([(0, y), (W, y)], fill=col)
    # thin clouds
    rnd = random.Random(11)
    for _ in range(18):
        cx, cy = rnd.randint(0, W), rnd.randint(10, 110)
        w = rnd.randint(14, 38)
        h = rnd.randint(1, 3)
        c = (20, 19, 40, 55)
        d.ellipse([cx, cy, cx + w, cy + h], fill=c)
    # faint stars
    for _ in range(40):
        x, y = rnd.randint(0, W - 1), rnd.randint(0, 90)
        v = rnd.choice([60, 80, 110, 140])
        d.point((x, y), fill=(v, v, min(255, v + 30), 255))
    # moon behind rain haze
    moon = img(W, H)
    md = ImageDraw.Draw(moon)
    md.ellipse([360, 30, 386, 56], fill=(150, 162, 190, 170))
    md.ellipse([364, 34, 382, 52], fill=(186, 198, 224, 190))
    halo = moon.filter(ImageFilter.GaussianBlur(16))
    im.alpha_composite(halo.point(lambda v: int(v * 0.55)))
    im.alpha_composite(moon)
    return im


# ---------------------------------------------------------------------------
# far skyline (tileable 512)
# ---------------------------------------------------------------------------
def build_far(seed=3):
    tw = 512
    im = img(tw, H)
    d = ImageDraw.Draw(im)

    def block(x, y, w, h, col, win_col=None, win_step=6, wrap=True):
        for off in (0, -tw, tw) if wrap else (0,):
            xx = x + off
            d.rectangle([xx, y, xx + w, y + h], fill=col)
            if win_col:
                rnd = random.Random(int(x * 7 + y))
                for wy in range(y + 4, y + h - 3, win_step):
                    for wx in range(xx + 3, xx + w - 3, 5):
                        if rnd.random() < 0.22:
                            d.rectangle([wx, wy, wx + 2, wy + 2], fill=win_col)
            # roof antenna
            if w > 30 and h > 40:
                d.line([(xx + w // 2, y), (xx + w // 2, y - 12)], fill=(14, 14, 30, 255))
                d.point((xx + w // 2, y - 13), fill=(255, 80, 80, 255))

    # back row
    xs = 0
    rnd = random.Random(seed)
    while xs < tw:
        w = rnd.choice([26, 34, 42, 52, 64])
        h = rnd.randint(46, 96)
        block(xs, 196 - h, w, h + 20, (14, 16, 36, 255), (40, 46, 78, 255), 8)
        xs += w
    # front row
    xs = 0
    while xs < tw:
        w = rnd.choice([36, 48, 58, 74])
        h = rnd.randint(70, 132)
        block(xs, 200 - h, w, h + 20, FAR, FAR_LIGHT, 7)
        xs += w
    # atmospheric haze over the skyline
    haze = vertical_gradient(tw, 120, [(24, 22, 52), (30, 26, 60)])
    haze.putalpha(64)
    im.alpha_composite(haze, (0, 96))
    return im


# ---------------------------------------------------------------------------
# mid facades (tileable 960)
# ---------------------------------------------------------------------------
def neon_sign(im, x, y, w, h, color, bars=None, frame=True, text=None):
    def shape(d):
        if frame:
            d.rectangle([x, y, x + w, y + h], outline=color, width=1)
        if bars:
            for i, (bx, by, bw, bh) in enumerate(bars):
                d.rectangle([x + bx, y + by, x + bx + bw, y + by + bh], fill=color)
        if text:
            tx0 = x + 3
            ty0 = y + max(2, (h - 7) // 2)
            for i, ch in enumerate(text):
                rows = FONT.get(ch, FONT[" "])
                for gy, row in enumerate(rows):
                    for gx, bit in enumerate(row):
                        if bit == "#":
                            px = tx0 + i * 6 + gx
                            py = ty0 + gy
                            d.rectangle([px, py, px, py], fill=color)
    im = glow_layer(im, shape, blur=6, gain=1.1)
    return im


GLYPHS3x5 = {
    "A": [(0, 1), (1, 0), (2, 1), (0, 2), (1, 2), (2, 2), (0, 3), (2, 3), (0, 4), (2, 4)],
    "B": [(0, 0), (1, 0), (0, 1), (2, 1), (0, 2), (1, 2), (0, 3), (2, 3), (0, 4), (1, 4)],
    "C": [(1, 0), (2, 0), (0, 1), (0, 2), (0, 3), (1, 4), (2, 4)],
    "D": [(0, 0), (1, 0), (0, 1), (2, 1), (0, 2), (2, 2), (0, 3), (2, 3), (0, 4), (1, 4)],
    "E": [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2), (1, 2), (0, 3), (0, 4), (1, 4), (2, 4)],
    "F": [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2), (1, 2), (0, 3), (0, 4)],
    "G": [(1, 0), (2, 0), (0, 1), (0, 2), (2, 2), (2, 3), (1, 4), (2, 4)],
    "H": [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2), (0, 3), (2, 3), (0, 4), (2, 4)],
    "I": [(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)],
    "J": [(2, 0), (2, 1), (2, 2), (0, 3), (2, 3), (1, 4)],
    "K": [(0, 0), (2, 0), (0, 1), (1, 1), (0, 2), (1, 2), (0, 3), (2, 3), (0, 4), (2, 4)],
    "L": [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 4), (2, 4)],
    "M": [(0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (2, 2), (0, 3), (2, 3), (0, 4), (2, 4)],
    "N": [(0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (2, 2), (0, 3), (2, 3), (0, 4), (2, 4)],
    "O": [(1, 0), (0, 1), (2, 1), (0, 2), (2, 2), (0, 3), (2, 3), (1, 4)],
    "P": [(0, 0), (1, 0), (0, 1), (2, 1), (0, 2), (1, 2), (0, 3), (0, 4)],
    "Q": [(1, 0), (0, 1), (2, 1), (0, 2), (2, 2), (0, 3), (1, 4)],
    "R": [(0, 0), (1, 0), (0, 1), (2, 1), (0, 2), (1, 2), (0, 3), (2, 3), (0, 4), (2, 4)],
    "S": [(1, 0), (0, 1), (1, 2), (2, 3), (1, 4)],
    "T": [(0, 0), (1, 0), (2, 0), (1, 1), (1, 2), (1, 3), (1, 4)],
    "U": [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2), (0, 3), (2, 3), (1, 4)],
    "V": [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2), (1, 3)],
    "W": [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2), (0, 3), (2, 3)],
    "X": [(0, 0), (2, 0), (1, 1), (1, 2), (0, 3), (2, 3), (0, 4), (2, 4)],
    "Y": [(0, 0), (2, 0), (1, 1), (1, 2), (1, 3), (1, 4)],
    "Z": [(0, 0), (1, 0), (2, 0), (2, 1), (1, 2), (0, 3), (0, 4), (1, 4), (2, 4)],
    "0": [(1, 0), (0, 1), (2, 1), (0, 2), (2, 2), (0, 3), (2, 3), (1, 4)],
    "1": [(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)],
    "2": [(0, 0), (1, 0), (2, 1), (1, 2), (0, 3), (0, 4), (1, 4), (2, 4)],
    "3": [(0, 0), (1, 0), (2, 1), (1, 2), (2, 3), (0, 4), (1, 4)],
    "4": [(0, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2), (2, 3), (2, 4)],
    "5": [(0, 0), (1, 0), (0, 1), (1, 2), (2, 3), (0, 4), (1, 4)],
    "6": [(1, 0), (0, 1), (0, 2), (1, 2), (2, 3), (0, 4), (1, 4)],
    "7": [(0, 0), (1, 0), (2, 0), (2, 1), (1, 2), (1, 3), (1, 4)],
    "8": [(1, 0), (0, 1), (2, 1), (1, 2), (0, 3), (2, 3), (1, 4)],
    "9": [(1, 0), (0, 1), (2, 1), (1, 2), (2, 3), (0, 4), (1, 4)],
    "-": [(0, 2), (1, 2), (2, 2)],
    " ": [],
}


def build_mid(seed=5):
    tw = 960
    im = img(tw, H)
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)

    def wrap(x, fn):
        for off in (0, -tw, tw):
            fn(x + off)

    # building faces
    xs = 0
    palette = [(30, 28, 50), (36, 31, 56), (26, 27, 48), (40, 33, 58)]
    while xs < tw:
        w = rnd.choice([96, 120, 144, 168])
        col = palette[(xs // 24) % len(palette)]
        h = rnd.randint(112, 150)
        top = 178 - h

        def face(x, col=col, w=w, h=h, top=top):
            d.rectangle([x, top, x + w, 186], fill=col)
            d.rectangle([x, top, x + w, top + 2], fill=tuple(min(255, c + 16) for c in col) + (255,))
            # window grid
            r = random.Random(x * 13 + 5)
            for wy in range(top + 14, 174, 22):
                for wx in range(x + 8, x + w - 10, 16):
                    lit = r.random() < 0.42
                    warm = r.random() < 0.62
                    c = (WINDOW if warm else WINDOW_C) if lit else (20, 20, 38)
                    d.rectangle([wx, wy, wx + 7, wy + 8], fill=c)
                    if lit:
                        d.rectangle([wx, wy, wx + 7, wy + 1], fill=tuple(min(255, v + 30) for v in c[:3]) + (255,))
                        # wet reflection under lit windows
                        d.rectangle([wx, wy + 9, wx + 7, wy + 10], fill=(c[0] // 3, c[1] // 3, c[2] // 3, 255))
                    # frame
                    d.line([(wx - 1, wy - 1), (wx + 8, wy - 1)], fill=tuple(max(0, v - 8) for v in col[:3]) + (255,))
                    d.line([(wx - 1, wy - 1), (wx - 1, wy + 8)], fill=tuple(max(0, v - 8) for v in col[:3]) + (255,))
        wrap(xs, face)

        # ground-floor shopfront
        def shop(x, w=w):
            d.rectangle([x + 4, 158, x + w - 4, 186], fill=(18, 18, 32, 255))
            d.rectangle([x + 4, 158, x + w - 4, 161], fill=(44, 38, 60, 255))
            for sy in range(165, 183, 3):
                d.line([(x + 8, sy), (x + w - 8, sy)], fill=(30, 30, 46, 255))
            d.rectangle([x + 10, 166, x + w - 10, 182], outline=(46, 44, 64, 255))
        wrap(xs, shop)
        xs += w

    # awnings
    for ax, ac in ((70, NEON_M), (300, NEON_C), (560, NEON_A), (820, NEON_G)):
        def awning(x, col=ac):
            d.polygon([(x, 152), (x + 88, 152), (x + 80, 162), (x + 8, 162)], fill=(38, 30, 48, 255))
            for i in range(0, 80, 10):
                d.polygon([(x + 4 + i, 154), (x + 12 + i, 154), (x + 10 + i, 161), (x + 2 + i, 161)],
                          fill=tuple(int(c * 0.55) for c in col) + (255,))
        wrap(ax, awning)

    # signs (tileable: keep well inside the band so no wrap needed)
    im = neon_sign(im, 56, 96, 26, 62, NEON_M, bars=[(3, 4, 20, 2), (3, 10, 14, 2), (3, 16, 20, 2),
                                                   (3, 22, 10, 2), (3, 28, 18, 2), (3, 34, 16, 2),
                                                   (3, 40, 20, 2), (3, 46, 12, 2), (3, 52, 18, 2)])
    im = neon_sign(im, 214, 60, 40, 20, NEON_C, text="OPEN 24")
    im = neon_sign(im, 366, 120, 20, 44, NEON_A, bars=[(3, 3, 14, 3), (3, 9, 8, 3), (3, 15, 14, 3),
                                                      (3, 21, 10, 3), (3, 27, 14, 3), (3, 33, 6, 3)])
    im = neon_sign(im, 520, 84, 54, 18, NEON_G, text="NOODLES")
    im = neon_sign(im, 668, 110, 22, 48, NEON_M, bars=[(4, 3, 14, 3), (4, 9, 14, 3), (4, 15, 6, 3),
                                                      (4, 21, 14, 3), (4, 27, 14, 3), (4, 33, 6, 3),
                                                      (4, 39, 14, 3)])
    im = neon_sign(im, 860, 54, 44, 18, NEON_C, text="BLOCK 07")

    # pipes and AC units
    d = ImageDraw.Draw(im)
    for px in (130, 470, 740):
        d.line([(px, 60), (px, 184)], fill=(22, 22, 38, 255), width=2)
        d.line([(px, 60), (px, 184)], fill=(34, 34, 54, 255), width=1)
        for py in range(70, 180, 26):
            d.rectangle([px - 3, py, px + 3, py + 3], fill=(40, 40, 60, 255))
    for ax in (250, 620, 900):
        d.rectangle([ax, 132, ax + 26, 150], fill=(24, 24, 40, 255), outline=(44, 44, 66, 255))
        for gy in range(135, 148, 4):
            d.line([(ax + 3, gy), (ax + 23, gy)], fill=(38, 38, 58, 255))
        d.ellipse([ax + 10, 138, ax + 20, 146], outline=(56, 56, 78, 255))

    # wet street level under the facades
    d.rectangle([0, 178, tw, 190], fill=(20, 20, 34, 255))
    d.line([(0, 179), (tw, 179)], fill=(48, 46, 68, 255))
    return im


# ---------------------------------------------------------------------------
# near street (unique 1800)
# ---------------------------------------------------------------------------
def build_near(world_w=1800):
    """Street surface.  The walkable lane (config/stage.json laneMin..laneMax)
    sits on the wide sidewalk; the road with the curb is behind it."""
    im = img(world_w, H)
    d = ImageDraw.Draw(im)
    rnd = random.Random(21)
    # road strip behind the curb
    d.rectangle([0, 178, world_w, 196], fill=(28, 28, 42, 255))
    d.rectangle([0, 178, world_w, 180], fill=(38, 38, 54, 255))
    for _ in range(1400):
        x = rnd.randrange(world_w)
        y = rnd.randrange(181, 195)
        v = rnd.choice([(26, 26, 40), (34, 34, 50), (22, 22, 34)])
        d.point((x, y), fill=v + (255,))
    for x in range(20, world_w, 120):
        d.rectangle([x, 184, x + 56, 187], fill=(150, 140, 90, 255))
        d.rectangle([x, 187, x + 56, 188], fill=(90, 84, 60, 255))
    # curb
    d.rectangle([0, 196, world_w, 203], fill=(64, 64, 80))
    d.line([(0, 196), (world_w, 196)], fill=(92, 92, 110))
    d.line([(0, 203), (world_w, 203)], fill=(30, 30, 42))
    for x in range(0, world_w, 48):
        d.line([(x, 196), (x, 203)], fill=(50, 50, 66))
    # sidewalk: the play field
    d.rectangle([0, 203, world_w, 270], fill=SIDEWALK)
    d.line([(0, 203), (world_w, 203)], fill=(56, 56, 74))
    for x in range(0, world_w, 48):
        d.line([(x, 203), (x, 270)], fill=(34, 34, 48, 255))
    for y in (224, 246, 266):
        d.line([(0, y), (world_w, y)], fill=(35, 35, 49, 255))
    for x in range(0, world_w, 96):
        d.line([(x + 48, 203), (x + 48, 270)], fill=(46, 46, 62, 255))
    # slab highlights
    for _ in range(400):
        x = rnd.randrange(world_w)
        y = rnd.randrange(202, 268)
        d.point((x, y), fill=rnd.choice([(46, 46, 62), (33, 33, 47), (50, 50, 68)]) + (255,))
    # puddles + neon reflections
    puddles = [(150, 230, 96, 12, NEON_C), (420, 236, 120, 13, NEON_M), (760, 228, 88, 10, NEON_A),
               (1030, 238, 140, 13, NEON_C), (1330, 230, 104, 11, NEON_M), (1610, 236, 120, 12, NEON_G)]
    for (px, py, pw, ph, col) in puddles:
        d.ellipse([px, py, px + pw, py + ph], fill=(18, 22, 40, 255))
        d.ellipse([px + 4, py + 2, px + pw - 6, py + ph - 3], fill=(26, 34, 56, 255))
        for k in range(3):
            yy = py + 2 + k * 3
            d.line([(px + 10 + k * 6, yy), (px + pw - 14 - k * 4, yy)],
                   fill=tuple(int(c * (0.45 - k * 0.1)) for c in col) + (255,))
    # cracks
    for _ in range(70):
        x = rnd.randrange(world_w)
        y = rnd.randrange(204, 264)
        d.line([(x, y), (x + rnd.randint(3, 9), y + rnd.choice([-1, 0, 1]))], fill=(32, 32, 46, 255))
    # drain grates
    for gx in (330, 900, 1420):
        d.rectangle([gx, 250, gx + 34, 260], fill=(16, 16, 26), outline=(52, 52, 66))
        for k in range(5):
            d.line([(gx + 3 + k * 7, 252), (gx + 3 + k * 7, 258)], fill=(38, 38, 50))
    # manholes sit in the road strip, not the lane
    for mx in (210, 640, 1080, 1500):
        d.ellipse([mx, 158, mx + 22, 167], fill=(34, 34, 48), outline=(52, 52, 68))
        for k in range(2):
            d.line([(mx + 5, 161 + k * 2), (mx + 17, 161 + k * 2)], fill=(28, 28, 40))

    # street furniture along the back edge of the sidewalk (behind gameplay)
    # lamp posts
    for lx in (240, 700, 1160, 1620):
        d.rectangle([lx, 118, lx + 3, 203], fill=(18, 18, 30, 255))
        d.rectangle([lx - 2, 199, lx + 5, 203], fill=(18, 18, 30, 255))
        d.polygon([(lx - 5, 118), (lx + 8, 118), (lx + 5, 124), (lx - 2, 124)], fill=(20, 20, 32, 255))
        d.rectangle([lx - 2, 124, lx + 5, 126], fill=(255, 196, 120, 255))
    # bollards and a bus-stop sign
    for bx in range(90, world_w, 260):
        d.rectangle([bx, 196, bx + 4, 204], fill=(36, 36, 50, 255))
        d.rectangle([bx, 194, bx + 4, 196], fill=(180, 172, 120, 255))
    # bus stop shelter on the road edge (background, never covers the lane)
    d.rectangle([1178, 150, 1180, 203], fill=(30, 30, 44, 255))
    d.rectangle([1162, 144, 1196, 160], fill=(20, 40, 48, 255), outline=(80, 200, 210, 255))
    for k in range(3):
        d.line([(1166, 148 + k * 4), (1192, 148 + k * 4)], fill=(120, 220, 226, 255))

    # neon spill light on the wet ground
    spills = [(166, NEON_C), (470, NEON_M), (790, NEON_A), (1050, NEON_C), (1350, NEON_M), (1630, NEON_G)]
    layer = img(world_w, H)
    ld = ImageDraw.Draw(layer)
    for (sx, col) in spills:
        for k in range(6):
            a = int(26 - k * 4)
            ld.rectangle([sx - 10 + k * 26, 203, sx + 40 + k * 26, 268], fill=col + (max(0, a),))
    layer = layer.filter(ImageFilter.GaussianBlur(9))
    im.alpha_composite(layer)
    return im


# ---------------------------------------------------------------------------
# foreground railing / lamps (tileable 480)
# ---------------------------------------------------------------------------
def build_fg():
    """Foreground layer: overhead cables + a low railing at the very bottom.
    Kept clear of the lane so it never hides a fighter."""
    tw = 480
    im = img(tw, H)
    d = ImageDraw.Draw(im)
    # overhead cables with a couple of paper lanterns
    for (x0, y0, x1, y1, sag) in ((0, 18, 180, 40, 14), (300, 30, 480, 12, 12), (120, 8, 360, 26, 16)):
        pts = []
        for k in range(0, 101):
            t = k / 100
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t + math.sin(t * math.pi) * sag
            pts.append((x, y))
        d.line(pts, fill=(10, 10, 20, 255), width=1)
    for lx, ly in ((212, 58), (302, 70)):
        d.line([(lx, ly), (lx, ly + 12)], fill=(10, 10, 20, 255))
        d.ellipse([lx - 4, ly + 10, lx + 4, ly + 18], fill=(52, 20, 26, 255))
        d.ellipse([lx - 3, ly + 11, lx + 3, ly + 16], fill=(196, 74, 64, 255))
        d.point((lx, ly + 13), fill=(255, 196, 150))
    # low railing that frames the bottom of the screen
    d.rectangle([0, 262, tw, 265], fill=(8, 8, 16, 255))
    d.rectangle([0, 268, tw, 270], fill=(8, 8, 16, 255))
    for px in range(0, tw, 16):
        d.rectangle([px, 262, px + 2, 270], fill=(8, 8, 16, 255))
    return im


# ---------------------------------------------------------------------------
# props / pickups / UI
# ---------------------------------------------------------------------------
def build_props():
    out = OUT / "props"
    out.mkdir(parents=True, exist_ok=True)
    # crate 34x34, two damage stages
    for stage in (0, 1):
        im = img(34, 34)
        d = ImageDraw.Draw(im)
        d.rectangle([1, 6, 32, 33], fill=(92, 58, 34), outline=(24, 16, 12))
        d.rectangle([1, 6, 32, 10], fill=(120, 78, 44), outline=(24, 16, 12))
        for k in range(1, 3):
            d.line([(2, 10 + k * 7), (31, 10 + k * 7)], fill=(66, 40, 24))
        d.line([(3, 7), (30, 32)], fill=(66, 40, 24))
        d.line([(30, 7), (3, 32)], fill=(66, 40, 24))
        # copper straps
        d.rectangle([6, 6, 9, 33], fill=(150, 104, 52))
        d.rectangle([24, 6, 27, 33], fill=(150, 104, 52))
        d.line([(1, 6), (32, 6)], fill=(176, 132, 72))
        if stage == 1:
            d.line([(12, 12), (18, 20), (15, 24)], fill=(28, 18, 12), width=2)
            d.line([(24, 16), (21, 26)], fill=(28, 18, 12), width=2)
            d.rectangle([9, 14, 13, 18], fill=(24, 16, 12))
        im.save(out / f"crate_{stage}.png")
    # barrel 26x36
    for stage in (0, 1):
        im = img(26, 36)
        d = ImageDraw.Draw(im)
        d.rectangle([1, 4, 24, 34], fill=(58, 70, 84), outline=(18, 20, 28))
        d.ellipse([1, 1, 24, 8], fill=(74, 86, 100), outline=(18, 20, 28))
        d.rectangle([1, 12, 24, 15], fill=(168, 84, 40))
        d.rectangle([1, 24, 24, 27], fill=(168, 84, 40))
        d.line([(4, 17), (4, 30)], fill=(88, 100, 116))
        d.line([(21, 17), (21, 30)], fill=(40, 48, 60))
        # hazard mark
        d.polygon([(10, 18), (17, 18), (13, 25)], fill=(240, 176, 60), outline=(40, 30, 10))
        d.point((13, 22), fill=(40, 30, 10))
        if stage == 1:
            d.line([(6, 8), (14, 22), (10, 28)], fill=(20, 22, 30), width=2)
            d.rectangle([14, 18, 20, 23], fill=(20, 22, 30))
        im.save(out / f"barrel_{stage}.png")
    # trash can 24x30
    for stage in (0, 1):
        im = img(24, 30)
        d = ImageDraw.Draw(im)
        d.polygon([(2, 6), (21, 6), (19, 29), (4, 29)], fill=(64, 70, 82), outline=(20, 22, 30))
        d.rectangle([1, 3, 22, 7], fill=(84, 92, 106), outline=(20, 22, 30))
        for k in range(4):
            d.line([(5, 10 + k * 4), (19, 10 + k * 4)], fill=(50, 56, 68))
        d.line([(6, 8), (18, 26)], fill=(92, 100, 114))
        if stage == 1:
            d.line([(14, 4), (10, 14), (16, 22)], fill=(24, 26, 34), width=2)
        im.save(out / f"trash_{stage}.png")
    # pickups 18x18
    health = img(18, 18)
    d = ImageDraw.Draw(health)
    d.rectangle([2, 3, 15, 15], fill=(30, 70, 66), outline=(10, 20, 22))
    d.rectangle([3, 4, 14, 14], outline=(86, 240, 255))
    d.polygon([(9, 5), (13, 5), (10, 9), (12, 9), (6, 14), (8, 10), (6, 10)], fill=(140, 252, 255), outline=(10, 30, 32))
    health.save(out / "pickup_health.png")
    score = img(18, 18)
    d = ImageDraw.Draw(score)
    d.rectangle([2, 3, 15, 15], fill=(58, 42, 16), outline=(24, 16, 8))
    d.rectangle([3, 4, 14, 14], outline=(255, 190, 80))
    d.ellipse([5, 6, 13, 14], fill=(240, 176, 70), outline=(80, 52, 20))
    d.point((9, 10), fill=(255, 232, 160))
    score.save(out / "pickup_score.png")
    # lamp glow sprite for the stage light pools
    gl = img(96, 96)
    gd = ImageDraw.Draw(gl)
    for r in range(46, 4, -3):
        a = int(10 + (46 - r) * 1.6)
        gd.ellipse([48 - r, 48 - r, 48 + r, 48 + r], fill=(255, 186, 110, min(140, a)))
    gl = gl.filter(ImageFilter.GaussianBlur(3))
    gl.save(out / "light_pool.png")


def build_ui():
    out = ROOT / "game/assets/ui"
    out.mkdir(parents=True, exist_ok=True)
    # logo: NEON GAUNTLET drawn with the project's 5x7 font + neon bloom
    W2, H2 = 300, 104
    im = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(4, 26), (W2 - 10, 12), (W2 - 4, H2 - 26), (14, H2 - 12)],
              fill=(8, 12, 24, 200), outline=(52, 220, 232, 255))
    d.line([(12, 30), (W2 - 20, 18)], fill=(120, 250, 255, 120), width=1)
    d.line([(20, H2 - 16), (W2 - 12, H2 - 28)], fill=(255, 180, 84, 200), width=1)

    def pixel_text(text, cx, y, scale, color, glow_color, blur=7, spacing=1):
        layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        adv = (5 + spacing) * scale
        x0 = cx - (len(text) * adv - spacing * scale) // 2
        for i, ch in enumerate(text.upper()):
            rows = FONT.get(ch, FONT[" "])
            for gy, row in enumerate(rows):
                for gx, bit in enumerate(row):
                    if bit == "#":
                        px = x0 + i * adv + gx * scale
                        py = y + gy * scale
                        ld.rectangle([px, py, px + scale - 1, py + scale - 1], fill=color)
        halo = layer.filter(ImageFilter.GaussianBlur(blur))
        # tint the halo
        tinted = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        tinted.paste(halo, (0, 0))
        td = ImageDraw.Draw(tinted)
        td.rectangle([0, 0, W2, H2], fill=None)
        glow = Image.new("RGBA", (W2, H2), glow_color + (0,))
        glow.putalpha(halo.getchannel("A").point(lambda v: int(v * 0.9)))
        im.alpha_composite(glow)
        im.alpha_composite(layer)

    pixel_text("NEON", W2 // 2, 16, 5, (255, 236, 246), (255, 66, 176), 9, spacing=2)
    pixel_text("GAUNTLET", W2 // 2, 60, 4, (226, 252, 255), (60, 220, 240), 8, spacing=1)
    d = ImageDraw.Draw(im)
    d.line([(58, 52), (W2 - 58, 48)], fill=(255, 180, 84, 220), width=1)
    im.save(out / "logo.png")

    # HUD panel strip (9-slice-ish, kept simple: one 200x26 bar background)
    hud = img(220, 30)
    hd = ImageDraw.Draw(hud)
    hd.rectangle([0, 0, 219, 29], fill=(8, 10, 18, 210))
    hd.rectangle([0, 0, 219, 29], outline=(38, 54, 66, 255))
    hd.line([(0, 1), (219, 1)], fill=(54, 200, 214, 90))
    hud.save(out / "hud_panel.png")

    # portrait badge
    port = img(34, 34)
    pd = ImageDraw.Draw(port)
    pd.rectangle([0, 0, 33, 33], fill=(12, 22, 30, 255), outline=(86, 240, 255, 255))
    pd.rectangle([2, 2, 31, 31], outline=(30, 62, 74, 255))
    port.save(out / "portrait_frame.png")

    # scanline overlay
    scan = img(8, 4)
    sd = ImageDraw.Draw(scan)
    sd.line([(0, 0), (7, 0)], fill=(0, 0, 0, 40))
    scan.save(out / "scanline.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "layers").mkdir(parents=True, exist_ok=True)
    build_sky().save(OUT / "layers/sky.png")
    build_far().save(OUT / "layers/far.png")
    build_mid().save(OUT / "layers/mid.png")
    build_near().save(OUT / "layers/near.png")
    build_fg().save(OUT / "layers/fg.png")
    build_props()
    build_ui()
    meta = {
        "id": "rain_district_1",
        "layers": {
            "sky": {"file": "layers/sky.png", "parallax": 0.0, "size": [W, H]},
            "far": {"file": "layers/far.png", "parallax": 0.15, "tile": True, "size": [512, H]},
            "mid": {"file": "layers/mid.png", "parallax": 0.45, "tile": True, "size": [960, H]},
            "near": {"file": "layers/near.png", "parallax": 1.0, "tile": False, "size": [1800, H]},
            "fg": {"file": "layers/fg.png", "parallax": 1.18, "tile": True, "size": [480, H]}
        },
        "props": {
            "crate": {"frames": ["props/crate_0.png", "props/crate_1.png"], "size": [34, 34]},
            "barrel": {"frames": ["props/barrel_0.png", "props/barrel_1.png"], "size": [26, 36]},
            "trash": {"frames": ["props/trash_0.png", "props/trash_1.png"], "size": [24, 30]}
        },
        "pickups": {
            "health": {"file": "props/pickup_health.png", "size": [18, 18]},
            "score": {"file": "props/pickup_score.png", "size": [18, 18]}
        },
        "lightPool": "props/light_pool.png"
    }
    (OUT / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("stage layers written")


if __name__ == "__main__":
    main()
