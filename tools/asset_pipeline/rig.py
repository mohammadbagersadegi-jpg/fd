"""Parametric pixel-art rig for the original characters.

Everything here is drawn from scratch at 1x into a 112x96 RGBA frame with the
feet anchor at (56, 88).  Poses are authored facing right; the engine mirrors
the frame when the character faces left.  Using one rig for every frame is what
keeps proportions, pivot points and palette identical across animations.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

from PIL import Image, ImageDraw

# Artwork is authored in a 112px-wide content box starting at x=0; the final
# frame is 128x96 with 8px of padding on each side so that wide lying-down poses
# never clip.  The exported anchor takes that padding into account.
CONTENT_W, FRAME_W, FRAME_H = 112, 128, 96
CONTENT_X = 8
AX, AY = 64, 88
OUT = (17, 14, 24, 255)


def C(r, g, b, a=255):
    return (r, g, b, a)


def shade(c, f):
    return (max(0, min(255, int(c[0] * f))), max(0, min(255, int(c[1] * f))),
            max(0, min(255, int(c[2] * f))), c[3] if len(c) > 3 else 255)


def add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def sub(p, q):
    return (p[0] - q[0], p[1] - q[1])


def length(v):
    return math.hypot(v[0], v[1])


def norm(v):
    d = length(v) or 1.0
    return (v[0] / d, v[1] / d)


def rot(v, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def lerp(p, q, t):
    return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)


def ik(a, target, l1, l2, bend=1.0):
    """Two-bone IK.  bend=+1 rotates the joint clockwise on screen."""
    d = sub(target, a)
    dist = math.hypot(*d)
    dist = max(0.5, min(dist, l1 + l2 - 0.6))
    base = math.atan2(d[1], d[0])
    cosang = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    ang = math.acos(max(-1.0, min(1.0, cosang)))
    j = (a[0] + math.cos(base + bend * ang) * l1,
         a[1] + math.sin(base + bend * ang) * l1)
    return j


@dataclass
class Palette:
    skin: tuple = C(230, 168, 111)
    skin_d: tuple = C(184, 120, 74)
    skin_h: tuple = C(248, 205, 148)
    hair: tuple = C(30, 24, 42)
    hair_h: tuple = C(62, 50, 78)
    jacket: tuple = C(28, 122, 114)
    jacket_d: tuple = C(18, 82, 78)
    jacket_h: tuple = C(52, 179, 164)
    jacket_in: tuple = C(12, 40, 43)
    pants: tuple = C(58, 63, 87)
    pants_d: tuple = C(38, 41, 60)
    pants_h: tuple = C(82, 88, 116)
    boot: tuple = C(25, 22, 34)
    boot_h: tuple = C(74, 64, 78)
    sole: tuple = C(120, 108, 96)
    copper: tuple = C(184, 92, 42)
    copper_d: tuple = C(111, 52, 24)
    copper_h: tuple = C(240, 138, 60)
    glow: tuple = C(99, 247, 255)
    glow_d: tuple = C(31, 169, 198)
    scarf: tuple = C(36, 170, 178)
    scarf_h: tuple = C(88, 232, 236)
    white: tuple = C(244, 241, 232)
    metal: tuple = C(112, 124, 132)
    metal_h: tuple = C(168, 180, 186)
    metal_d: tuple = C(64, 72, 78)
    rim: tuple = C(110, 240, 255)
    ember: tuple = C(255, 156, 64)


@dataclass
class Look:
    bulk: int = 0
    helmet: bool = False
    scarf: bool = True
    weapon: bool = False
    gauntlets: bool = True
    hair: str = "spikes"   # spikes | bald
    belt: bool = True


@dataclass
class Pose:
    hip: tuple = (56, 61)
    lean: float = 2.0
    head_shift: tuple = (0, 0)
    head_tilt: float = 0.0
    hand_f: tuple = (67, 50)
    hand_b: tuple = (49, 53)
    foot_f: tuple = (64, 88)
    foot_b: tuple = (49, 88)
    foot_f_angle: float = 0.0
    foot_b_angle: float = 0.0
    face: str = "neutral"
    scarf_phase: float = 0.0
    spark: int = 0
    surge: int = 0
    impact: int = 0
    pipe_angle: float = -115.0
    dust: int = 0
    tilt: float = 0.0
    lying: int = 0


class Frame:
    def __init__(self):
        self.img = Image.new("RGBA", (CONTENT_W, FRAME_H), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def poly(self, pts: Iterable[tuple], fill, outline=OUT, width=1):
        pts = [(int(round(x)), int(round(y))) for x, y in pts]
        if len(pts) < 3:
            return
        self.d.polygon(pts, fill=fill, outline=outline, width=width)

    def line(self, pts, fill, width=1):
        pts = [(int(round(x)), int(round(y))) for x, y in pts]
        self.d.line(pts, fill=fill, width=width)

    def dot(self, p, fill, r=1, outline=None):
        x, y = int(round(p[0])), int(round(p[1]))
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=outline)

    def box(self, x0, y0, x1, y1, fill, outline=None):
        self.d.rectangle([int(x0), int(y0), int(x1), int(y1)], fill=fill, outline=outline)

    def limb(self, p0, p1, w0, w1, fill, outline=OUT, hi=None, hi_side=-1, round_ends=True):
        u = norm(sub(p1, p0))
        n = (-u[1], u[0])
        a0 = add(p0, (n[0] * w0 / 2, n[1] * w0 / 2))
        b0 = sub(p0, (n[0] * w0 / 2, n[1] * w0 / 2))
        a1 = add(p1, (n[0] * w1 / 2, n[1] * w1 / 2))
        b1 = sub(p1, (n[0] * w1 / 2, n[1] * w1 / 2))
        self.poly([a0, a1, b1, b0], fill, outline)
        if round_ends:
            if w0 >= 6:
                self.dot(p0, fill, int(w0 // 2) - 1, outline)
            if w1 >= 6:
                self.dot(p1, fill, int(w1 // 2) - 1, outline)
        if hi:
            off = (n[0] * hi_side * max(0.5, (w0 - 1) / 2 - 0.6),
                   n[1] * hi_side * max(0.5, (w0 - 1) / 2 - 0.6))
            off1 = (n[0] * hi_side * max(0.5, (w1 - 1) / 2 - 0.6),
                    n[1] * hi_side * max(0.5, (w1 - 1) / 2 - 0.6))
            self.line([add(p0, off), add(p1, off1)], hi, 1)


def boot(f: Frame, foot, angle, pal: Palette, front=True, bulky=False):
    """Boot with the sole touching ``foot`` (the ground anchor when standing)."""
    x, y = foot
    w = 5 if not bulky else 6
    # shaft
    ax = (x - 1.5, y - 8)
    f.limb((x - 1, y - 8), (x + 0.5, y - 3), w, w + 1, pal.boot, hi=pal.boot_h, hi_side=1)
    # toe box pointing forward
    toe = (x + (8 if not bulky else 9), y - 1)
    f.limb((x, y - 4), toe, 4, 3, pal.boot, hi=pal.boot_h, hi_side=-1)
    f.line([(x - 2, y - 1), (toe[0] - 1, y - 1), (toe[0], y)], pal.sole, 2)
    f.dot((x + 2, y - 5), pal.boot_h, 0)
    if front:
        f.line([(x + 1, y - 7), (x + 3, y - 7)], pal.sole, 1)
        f.line([(x + 1, y - 6), (x + 3, y - 6)], pal.sole, 1)


def gauntlet(f: Frame, elbow, hand, pal: Palette, spark=0):
    u = norm(sub(hand, elbow))
    start = add(elbow, (u[0] * 3, u[1] * 3))
    f.limb(start, hand, 7, 6, pal.copper_d, round_ends=False)
    f.limb(start, hand, 5, 4, pal.copper, round_ends=False)
    n = (-u[1], u[0])
    f.line([add(start, (n[0] * 2, n[1] * 2)), add(hand, (n[0] * 2, n[1] * 2))], pal.copper_h, 1)
    f.line([add(start, (-n[0] * 2, -n[1] * 2)), add(hand, (-n[0] * 2, -n[1] * 2))], pal.glow_d, 1)
    # cuff ring
    cuff = add(start, (u[0] * 1, u[1] * 1))
    f.line([add(cuff, (n[0] * 3, n[1] * 3)), add(cuff, (-n[0] * 3, -n[1] * 3))], pal.copper_h, 1)
    # fist
    fist = add(hand, (u[0] * 1.5, u[1] * 1.5))
    f.dot(fist, pal.boot, 3, OUT)
    f.line([add(fist, (n[0] * 2, n[1] * 2 - 1)), add(fist, (u[0] * 2, u[1] * 2))], pal.copper_h, 1)
    if spark:
        f.line([add(fist, (2, -3)), add(fist, (4, -2)), add(fist, (3, 0))], pal.glow, 1)
        if spark > 1:
            f.line([add(fist, (1, -5)), add(fist, (3, -6)), add(fist, (5, -4))], pal.white, 1)


def arm(f: Frame, shoulder, target, pal: Palette, look: Look, front=True, spark=0):
    l1, l2 = 11.5, 11.0
    bend = 1.0 if front else -1.0
    elbow = ik(shoulder, target, l1, l2, bend=bend)
    sleeve_end = lerp(shoulder, elbow, 0.72)
    sleeve_col = pal.jacket if front else pal.jacket_d
    skin_col = pal.skin if front else pal.skin_d
    f.limb(shoulder, sleeve_end, 7 if front else 6, 6, sleeve_col, hi=pal.jacket_h if front else None,
           hi_side=1)
    f.limb(sleeve_end, elbow, 5, 4, skin_col)
    f.limb(elbow, target, 4, 3, skin_col)
    if look.gauntlets:
        gauntlet(f, elbow, target, pal, spark)
    else:
        f.dot(target, pal.boot if not front else C(46, 38, 44), 2, OUT)
    return elbow


def leg(f: Frame, hip, foot, pal: Palette, front=True, bulky=False, foot_angle=0.0):
    l1, l2 = 12.5, 12.5
    target = (foot[0], foot[1] - 4)
    knee = ik(hip, target, l1, l2, bend=-1.0)
    w = 9 if bulky else 8
    pant = pal.pants if front else pal.pants_d
    hi = pal.pants_h if front else shade(pal.pants_h, 0.7)
    f.limb(hip, knee, w + 2, w, pant, hi=hi, hi_side=-1, round_ends=False)
    f.limb(knee, target, w, w - 2, pant, hi=hi, hi_side=-1, round_ends=False)
    if front:
        # knee pad + cargo pocket
        f.poly([add(knee, (-3, -3)), add(knee, (3, -3)), add(knee, (4, 2)), add(knee, (-4, 2))],
               pal.pants_d, OUT)
        f.line([add(knee, (-2, -1)), add(knee, (2, -1))], pal.pants_h, 1)
        f.box(knee[0] - 6, knee[1] + 3, knee[0] - 3, knee[1] + 7, pal.pants_d)
    f.dot(target, pal.boot, 3, OUT)
    boot(f, foot, foot_angle, pal, front=front, bulky=bulky)
    return knee


def head(f: Frame, center, pal: Palette, look: Look, face="neutral", axis=(0, 1)):
    """8-10 px stylised head in 3/4 view.

    ``axis`` is the unit vector from the head towards the torso.  Standing
    characters pass (0, 1); characters lying on the ground pass a horizontal
    axis so the neck stays attached and the head silhouette rotates with the
    body instead of floating next to it.
    """
    cx, cy = int(center[0]), int(center[1])
    ax, ay = axis
    lying = abs(ax) > 0.7
    # neck: short, along the body axis, so it always meets the shoulders
    n0 = (cx + ax * 4, cy + ay * 4)
    n1 = (cx + ax * 11, cy + ay * 11)
    f.limb(n0, n1, 5, 6, pal.skin_d, round_ends=False)
    f.line([(n0[0] - 2, n0[1] - 2), (n0[0] + 2, n0[1] + 2)], shade(pal.skin_d, 0.82), 1)

    if lying:
        # head lying on its side: hair mass below, face towards the screen top
        f.poly([(cx - 8, cy - 2), (cx - 6, cy - 7), (cx + 5, cy - 7), (cx + 7, cy - 1),
                (cx + 7, cy + 4), (cx - 6, cy + 4), (cx - 8, cy + 1)], pal.skin, OUT)
        # ear
        f.dot((cx - 2, cy + 1), pal.skin_d, 1)
        # hair across the side of the head
        if look.hair == "spikes":
            f.poly([(cx - 9, cy + 1), (cx - 6, cy + 4), (cx + 6, cy + 4), (cx + 8, cy + 1),
                    (cx + 7, cy - 3), (cx - 7, cy - 3)], pal.hair, OUT)
            f.poly([(cx - 8, cy + 3), (cx - 12, cy + 7), (cx - 5, cy + 8)], pal.hair, OUT)
            f.poly([(cx + 2, cy + 3), (cx + 5, cy + 9), (cx + 8, cy + 3)], pal.hair, OUT)
            f.line([(cx - 4, cy + 1), (cx + 3, cy + 1)], pal.hair_h, 1)
        # eye + brow on the up-facing side
        f.line([(cx - 4, cy - 5), (cx + 1, cy - 5)], pal.hair, 1)
        f.line([(cx - 3, cy - 4), (cx - 1, cy - 4)], pal.hair, 1)
        f.line([(cx + 2, cy - 4), (cx + 4, cy - 4)], shade(pal.skin_d, 0.9), 1)
        f.line([(cx - 7, cy - 1), (cx - 7, cy + 2)], pal.rim, 1)
        return

    if look.hair == "spikes":
        # back hair mass + swept spikes
        f.poly([(cx - 7, cy - 2), (cx - 5, cy - 7), (cx + 4, cy - 7), (cx + 3, cy - 2)],
               pal.hair, OUT)
        f.poly([(cx - 6, cy - 4), (cx - 11, cy - 6), (cx - 7, cy + 2)], pal.hair, OUT)
        f.poly([(cx - 4, cy - 6), (cx - 6, cy - 13), (cx, cy - 7)], pal.hair, OUT)
        f.poly([(cx + 1, cy - 7), (cx + 3, cy - 13), (cx + 6, cy - 5)], pal.hair, OUT)
        f.line([(cx - 4, cy - 11), (cx - 3, cy - 8)], pal.hair_h, 1)
        f.line([(cx + 2, cy - 11), (cx + 4, cy - 8)], pal.hair_h, 1)
        f.line([(cx - 6, cy - 5), (cx - 4, cy - 4)], pal.hair_h, 1)
    # face silhouette: forehead -> brow -> nose -> chin
    f.poly([(cx - 5, cy - 4), (cx + 3, cy - 4), (cx + 6, cy - 1), (cx + 6, cy + 2),
            (cx + 4, cy + 3), (cx + 4, cy + 6), (cx - 2, cy + 6), (cx - 5, cy + 3)],
           pal.skin, OUT)
    # ear
    f.poly([(cx - 5, cy + 0), (cx - 7, cy + 1), (cx - 6, cy + 3), (cx - 4, cy + 3)], pal.skin, OUT)
    f.dot((cx - 5, cy + 2), pal.skin_d, 0)
    # fringe over the forehead
    f.poly([(cx - 6, cy - 3), (cx - 4, cy - 6), (cx + 4, cy - 6), (cx + 6, cy - 2),
            (cx + 2, cy - 2), (cx - 1, cy - 1), (cx - 4, cy - 2)], pal.hair, OUT)
    f.line([(cx - 2, cy - 4), (cx + 2, cy - 4)], pal.hair_h, 1)
    # sideburn
    f.poly([(cx - 6, cy - 2), (cx - 5, cy - 2), (cx - 5, cy + 2), (cx - 6, cy + 1)], pal.hair)
    # brow
    if face == "pain":
        f.line([(cx + 1, cy + 0), (cx + 5, cy - 1)], pal.hair, 1)
    else:
        f.line([(cx + 1, cy - 1), (cx + 5, cy - 1)], pal.hair, 1)
    # eye
    if face in ("strain", "shout"):
        f.line([(cx + 2, cy + 1), (cx + 5, cy + 1)], pal.hair, 1)
    elif face == "pain":
        f.line([(cx + 2, cy + 2), (cx + 5, cy + 2)], pal.hair, 1)
    else:
        f.box(cx + 2, cy + 1, cx + 4, cy + 2, pal.white)
        f.box(cx + 4, cy + 1, cx + 4, cy + 2, pal.hair)
    # nose
    f.dot((cx + 6, cy + 1), pal.skin_d, 0)
    f.dot((cx + 5, cy + 2), pal.skin_d, 0)
    # mouth
    if face == "shout":
        f.box(cx + 1, cy + 4, cx + 4, cy + 5, C(74, 30, 34))
        f.line([(cx + 1, cy + 4), (cx + 4, cy + 4)], pal.skin_h, 1)
    elif face in ("strain", "pain"):
        f.line([(cx + 1, cy + 4), (cx + 4, cy + 5)], shade(pal.skin_d, 0.85), 1)
    else:
        f.line([(cx + 1, cy + 4), (cx + 4, cy + 4)], shade(pal.skin_d, 0.9), 1)
    f.line([(cx - 2, cy + 6), (cx + 3, cy + 6)], shade(pal.skin_d, 0.9), 1)
    f.line([(cx - 7, cy - 2), (cx - 7, cy + 1)], pal.rim, 1)


def scarf(f: Frame, anchor, pal: Palette, phase: float, lift=0.0):
    """Two short cloth tails that hang down/back from the neck and wave."""
    for i, (ln, wid) in enumerate(((15, 5), (11, 4))):
        ph = phase + i * 2.1
        pts = []
        for s_ in range(5):
            t = s_ / 4
            x = anchor[0] - ln * t
            y = anchor[1] + (5 + 6 * t) + math.sin(ph + t * 2.6) * (1.2 + 1.6 * t) - lift * 0.35 * t
            pts.append((x, y))
        for s_ in range(len(pts) - 1):
            t0, t1 = s_ / 4, (s_ + 1) / 4
            w0 = wid * (1 - t0) + 1.2
            w1 = wid * (1 - t1) + 1.2
            u = norm(sub(pts[s_ + 1], pts[s_]))
            n = (-u[1], u[0])
            quad = [add(pts[s_], (n[0] * w0 / 2, n[1] * w0 / 2)),
                    add(pts[s_ + 1], (n[0] * w1 / 2, n[1] * w1 / 2)),
                    add(pts[s_ + 1], (-n[0] * w1 / 2, -n[1] * w1 / 2)),
                    add(pts[s_], (-n[0] * w0 / 2, -n[1] * w0 / 2))]
            f.poly(quad, pal.scarf if i == 0 else shade(pal.scarf, 0.78))
        f.line([(int(x), int(y)) for x, y in pts[1:]], pal.scarf_h, 1)


def torso(f: Frame, pelvis, lean, pal: Palette, look: Look):
    up = rot((0, -1), lean)
    right = rot((1, 0), lean)
    shoulder = add(pelvis, (up[0] * 24, up[1] * 24))
    half_s = 10 + look.bulk * 2
    half_w = 8 + look.bulk
    # shorts / hips
    f.poly([add(pelvis, (-half_w - 1, -3)), add(pelvis, (half_w + 1, -3)),
            add(pelvis, (half_w - 1, 5)), add(pelvis, (-half_w + 1, 5))], pal.pants)
    # jacket body
    pts = [add(shoulder, (right[0] * -half_s, right[1] * -half_s)),
           add(shoulder, (right[0] * half_s, right[1] * half_s)),
           add(pelvis, (right[0] * half_w, right[1] * half_w)),
           add(pelvis, (right[0] * -half_w, right[1] * -half_w))]
    f.poly(pts, pal.jacket)
    # shaded back panel
    f.poly([pts[0], add(shoulder, (right[0] * -2, right[1] * -2)),
            add(pelvis, (right[0] * -2, right[1] * -2)), pts[3]], pal.jacket_d)
    # open front: dark inner shirt stripe
    f.poly([add(shoulder, (right[0] * 1, 1)), add(shoulder, (right[0] * 6, 1)),
            add(pelvis, (right[0] * 5, -1)), add(pelvis, (right[0] * 1, -1))], pal.jacket_in)
    # lapels (copper) framing the opening
    f.line([add(shoulder, (right[0] * 1, 1)), add(pelvis, (right[0] * 1, -1))], pal.copper_d, 1)
    f.line([add(shoulder, (right[0] * 6, 1)), add(pelvis, (right[0] * 5, -1))], pal.copper, 1)
    # front edge highlight + rim light on the back
    f.line([pts[1], add(pelvis, (right[0] * half_w, right[1] * half_w))], pal.jacket_h, 1)
    f.line([pts[0], pts[3]], pal.rim, 1)
    # cargo pocket on the chest
    px, py = add(pelvis, (-5 + look.bulk, -12))
    f.box(px - 3, py - 3, px + 2, py + 2, pal.jacket_d)
    f.line([(px - 3, py - 3), (px + 2, py - 3)], pal.jacket_h, 1)
    # lightning emblem on the front panel
    bx, by = add(pelvis, (right[0] * 9, -15))
    if look.gauntlets:
        f.poly([(bx - 1, by - 4), (bx + 3, by - 4), (bx + 1, by - 1), (bx + 3, by - 1),
                (bx - 2, by + 5), (bx - 1, by + 1), (bx - 3, by + 1)], pal.glow, OUT)
    # belt
    if look.belt:
        f.box(pelvis[0] - half_w, pelvis[1], pelvis[0] + half_w, pelvis[1] + 2, C(42, 30, 32), OUT)
        f.box(pelvis[0] + 1, pelvis[1], pelvis[0] + 4, pelvis[1] + 2, pal.copper_h, OUT)
    # shoulder plates sit on top of the deltoids, not in front of the arms
    for side, col in ((1, pal.copper), (-1, shade(pal.copper, 0.85))):
        p_ = add(shoulder, (right[0] * side * (half_s - 3), right[1] * side * (half_s - 3)))
        f.poly([add(p_, (-4, -2)), add(p_, (3, -3)), add(p_, (4, 1)), add(p_, (-3, 2))], col, OUT)
        f.line([add(p_, (-3, -1)), add(p_, (2, -2))], pal.copper_h, 1)


def draw_character(pose: Pose, pal: Palette, look: Look) -> Image.Image:
    f = Frame()
    _pad = True
    up = rot((0, -1), pose.lean)
    right = rot((1, 0), pose.lean)
    pelvis = pose.hip
    shoulder_base = add(pelvis, (up[0] * 24, up[1] * 24))
    neck = add(shoulder_base, (up[0] * 4, up[1] * 4))
    head_c = add(neck, (up[0] * 8 + pose.head_shift[0], up[1] * 8 + pose.head_shift[1]))
    sh_f = add(shoulder_base, (right[0] * 4, right[1] * 4))
    sh_b = add(shoulder_base, (-right[0] * 4, -right[1] * 4))
    hip_f = add(pelvis, (right[0] * 3, right[1] * 3))
    hip_b = add(pelvis, (-right[0] * 3, -right[1] * 3))

    if look.scarf:
        scarf(f, add(neck, (-2, 2)), pal, pose.scarf_phase, lift=-pose.hip[1] + 61)

    # back leg and arm
    leg(f, hip_b, pose.foot_b, pal, front=False, bulky=look.bulk > 0, foot_angle=pose.foot_b_angle)
    arm(f, sh_b, pose.hand_b, pal, look, front=False, spark=max(0, pose.spark - 1))

    # torso + front leg
    torso(f, pelvis, pose.lean, pal, look)
    leg(f, hip_f, pose.foot_f, pal, front=True, bulky=look.bulk > 0, foot_angle=pose.foot_f_angle)

    _ax = norm(sub(shoulder_base, head_c)) if (shoulder_base[0] - head_c[0]) or (shoulder_base[1] - head_c[1]) else (0, 1)
    head(f, head_c, pal, look, face=pose.face, axis=_ax)

    # front arm last so punches read clearly
    arm(f, sh_f, pose.hand_f, pal, look, front=True, spark=pose.spark)

    if look.weapon:
        elbow = ik(sh_f, pose.hand_f, 11.5, 11.0, bend=1.0)
        u = rot((1, 0), pose.pipe_angle)
        start = pose.hand_f
        tip = add(start, (u[0] * 30, u[1] * 30))
        f.limb(start, tip, 4, 3, pal.metal_d, round_ends=False)
        f.limb(start, tip, 2, 2, pal.metal, round_ends=False)
        f.line([add(start, (0, -1)), add(tip, (0, -1))], pal.metal_h, 1)
        f.dot(tip, pal.metal_d, 2, OUT)
        f.line([add(start, (-3, 0)), add(start, (2, 0))], C(60, 46, 38), 2)

    # baked electrical effects
    if pose.surge:
        for k in range(3):
            a = (head_c[0] + (k - 1) * 9, head_c[1] + 16)
            pts = [a]
            for s in range(4):
                pts.append((a[0] + (s + 1) * 4 * (1 if k != 1 else -1),
                            a[1] + (4 if s % 2 else -4) + k * 5))
            f.line(pts, pal.glow if k != 1 else pal.white, 1)
        f.line([(pose.hand_f[0] - 1, pose.hand_f[1] - 2), (pose.hand_f[0] + 5, pose.hand_f[1] - 7),
                (pose.hand_f[0] + 2, pose.hand_f[1] + 3)], pal.white, 1)
    if pose.impact:
        x, y = pose.hand_f
        for dx, dy in ((7, -5), (9, 0), (7, 5), (12, -2)):
            f.line([(x + 3, y), (x + dx, y + dy)], pal.glow, 1)
        f.dot((x + 4, y), pal.white, 1)
    if pose.dust:
        for dx, dy in ((-7, 1), (-10, -1), (7, 1), (10, 0)):
            f.dot((pose.foot_f[0] + dx, 87 + dy), C(120, 120, 132), 1)

    return pad(f.img)


def pad(content: Image.Image) -> Image.Image:
    out = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    out.alpha_composite(content, (CONTENT_X, 0))
    return out


# ---------------------------------------------------------------------------
# Poses
# ---------------------------------------------------------------------------

def foot_cycle(phase: float, stride=14.0, lift=6.0, center=56.0):
    phase = phase % 1.0
    if phase < 0.62:
        t = phase / 0.62
        return (center + stride / 2 - stride * t, AY)
    t = (phase - 0.62) / 0.38
    return (center - stride / 2 + stride * t, AY - lift * math.sin(math.pi * t))


def walk_pose(i: int, n: int, look: Look) -> Pose:
    p = i / n
    ff = foot_cycle(p)
    fb = foot_cycle(p + 0.5)
    hip_y = 62 - 1.0 * math.cos(4 * math.pi * p)
    swing = math.sin(2 * math.pi * p)
    return Pose(
        hip=(56, hip_y), lean=4,
        hand_f=(66 - swing * 4, 62 + abs(swing) * 1), hand_b=(47 + swing * 4, 63 - abs(swing)),
        foot_f=ff, foot_b=fb,
        face="neutral", scarf_phase=p * 6.28,
        foot_f_angle=4 if ff[1] < AY else 0, foot_b_angle=4 if fb[1] < AY else 0,
    )


def idle_pose(i: int, look: Look) -> Pose:
    bob = (0, 1, 1, 0, 0, 1)[i % 6]
    sway = math.sin(i / 6 * 6.283)
    return Pose(
        hip=(56, 62 - bob), lean=3,
        hand_f=(67 + sway, 49 + bob), hand_b=(50, 53 + bob),
        foot_f=(64, 88), foot_b=(49, 88),
        foot_f_angle=0, foot_b_angle=6,
        spark=1 if i % 3 == 2 else 0,
        scarf_phase=i * 1.1,
    )


def walk_pose(i: int, n: int, look: Look) -> Pose:
    p = i / n
    ff = foot_cycle(p)
    fb = foot_cycle(p + 0.5)
    hip_y = 62 - 1.0 * math.cos(4 * math.pi * p)
    swing = math.sin(2 * math.pi * p)
    return Pose(
        hip=(56, hip_y), lean=5,
        hand_f=(66 - swing * 3, 51 + abs(swing) * 1), hand_b=(50 + swing * 3, 55),
        foot_f=ff, foot_b=fb,
        face="neutral", scarf_phase=p * 6.28,
        foot_f_angle=6 if ff[1] < AY else 0, foot_b_angle=6 if fb[1] < AY else 0,
    )


def _mk(base):
    def mk(**kw):
        d = dict(base)
        d.update(kw)
        return Pose(**d)
    return mk


def attack1_pose(i: int, look: Look) -> Pose:
    mk = _mk(dict(hip=(56, 61), foot_f=(65, 88), foot_b=(49, 88), lean=3))
    p = [
        mk(lean=0, hand_f=(53, 56), hand_b=(66, 54), face="strain", scarf_phase=0.2),
        mk(hip=(57, 61), lean=8, hand_f=(81, 51), hand_b=(48, 58), foot_f=(67, 88),
             face="strain", impact=1, scarf_phase=1.2, spark=1),
        mk(hip=(57, 61), lean=9, hand_f=(82, 52), hand_b=(47, 59), foot_f=(67, 88),
             face="strain", impact=1, scarf_phase=1.6),
        mk(lean=2, hand_f=(65, 55), hand_b=(50, 60), face="neutral", scarf_phase=2.2),
        mk(lean=2, hand_f=(66, 62), hand_b=(49, 63), face="neutral", scarf_phase=2.8),
    ]
    return p[i]


def attack2_pose(i: int, look: Look) -> Pose:
    mk = _mk(dict(hip=(56, 60), foot_f=(66, 88), foot_b=(48, 88), lean=3))
    p = [
        mk(lean=-3, hand_f=(58, 60), hand_b=(44, 52), face="strain", scarf_phase=0.1),
        mk(lean=12, hip=(58, 60), hand_f=(63, 45), hand_b=(78, 48), foot_f=(69, 88),
             face="shout", impact=1, spark=2, scarf_phase=1.4),
        mk(lean=14, hip=(58, 60), hand_f=(62, 46), hand_b=(80, 50), foot_f=(69, 88),
             face="shout", impact=1, spark=2, scarf_phase=1.8),
        mk(lean=3, hand_f=(65, 57), hand_b=(60, 56), face="neutral", scarf_phase=2.4),
        mk(lean=2, hand_f=(66, 62), hand_b=(48, 63), face="neutral", scarf_phase=3.0),
    ]
    return p[i]


def attack3_pose(i: int, look: Look) -> Pose:
    mk = _mk(dict(hip=(56, 61), hand_f=(68, 62), hand_b=(44, 62), foot_f=(64, 88), foot_b=(50, 88), lean=3))
    p = [
        mk(hip=(55, 63), lean=6, hand_f=(60, 58), hand_b=(45, 54), foot_f=(62, 88), foot_b=(48, 88),
             face="strain", scarf_phase=0.2),
        mk(hip=(55, 60), lean=-6, hand_f=(56, 52), hand_b=(42, 56), foot_f=(63, 88), foot_b=(48, 88),
             face="strain", scarf_phase=0.9),
        mk(hip=(56, 58), lean=-12, hand_f=(50, 48), hand_b=(38, 58), foot_f=(76, 52), foot_b=(56, 86),
             foot_f_angle=-20, face="shout", impact=1, spark=1, scarf_phase=1.5),
        mk(hip=(56, 58), lean=-13, hand_f=(49, 49), hand_b=(37, 59), foot_f=(78, 54), foot_b=(56, 86),
             foot_f_angle=-24, face="shout", impact=1, spark=1, scarf_phase=1.9),
        mk(hip=(55, 62), lean=2, hand_f=(58, 58), hand_b=(44, 60), foot_f=(68, 80), foot_b=(50, 88),
             foot_f_angle=10, face="strain", scarf_phase=2.5),
        mk(hip=(56, 61), lean=3, hand_f=(66, 62), hand_b=(49, 63), foot_f=(64, 88), foot_b=(50, 88),
             face="neutral", scarf_phase=3.1),
    ]
    return p[i]


def special_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(56, 64), lean=8, hand_f=(64, 55), hand_b=(49, 56), foot_f=(66, 88), foot_b=(47, 88),
             face="strain", spark=1, scarf_phase=0.2),
        Pose(hip=(56, 62), lean=-4, hand_f=(48, 50), hand_b=(38, 52), foot_f=(67, 88), foot_b=(46, 88),
             face="shout", spark=2, surge=1, scarf_phase=1.0),
        Pose(hip=(56, 60), lean=0, hand_f=(82, 58), hand_b=(40, 60), foot_f=(70, 88), foot_b=(45, 88),
             face="shout", spark=2, surge=1, impact=1, scarf_phase=1.8),
        Pose(hip=(56, 60), lean=0, hand_f=(84, 60), hand_b=(41, 61), foot_f=(70, 88), foot_b=(45, 88),
             face="shout", spark=2, surge=1, impact=1, scarf_phase=2.2),
        Pose(hip=(56, 62), lean=4, hand_f=(70, 62), hand_b=(46, 62), foot_f=(66, 88), foot_b=(48, 88),
             face="strain", spark=1, scarf_phase=2.8),
        Pose(hip=(56, 63), lean=6, hand_f=(64, 66), hand_b=(44, 65), foot_f=(64, 88), foot_b=(49, 88),
             face="pain", scarf_phase=3.3),
        Pose(hip=(56, 62), lean=4, hand_f=(63, 64), hand_b=(46, 64), foot_f=(63, 88), foot_b=(49, 88),
             face="strain", spark=1, scarf_phase=3.8),
        Pose(hip=(56, 61), lean=3, hand_f=(65, 63), hand_b=(48, 64), foot_f=(63, 88), foot_b=(50, 88),
             face="neutral", scarf_phase=4.2),
    ]
    return p[i]


def jump_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(56, 64), lean=8, hand_f=(62, 62), hand_b=(48, 64), foot_f=(63, 88), foot_b=(50, 88),
             face="strain", scarf_phase=0.4, dust=1),
        Pose(hip=(56, 57), lean=2, hand_f=(70, 48), hand_b=(44, 56), foot_f=(62, 84), foot_b=(49, 86),
             face="strain", scarf_phase=1.2),
        Pose(hip=(56, 54), lean=0, hand_f=(68, 55), hand_b=(44, 55), foot_f=(62, 80), foot_b=(50, 82),
             face="neutral", scarf_phase=2.0),
        Pose(hip=(56, 63), lean=8, hand_f=(62, 64), hand_b=(48, 64), foot_f=(63, 88), foot_b=(49, 88),
             face="strain", scarf_phase=2.8, dust=1),
    ]
    return p[i]


def jump_attack_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(56, 56), lean=10, hand_f=(60, 50), hand_b=(46, 56), foot_f=(63, 84), foot_b=(50, 88),
             face="strain", scarf_phase=0.8),
        Pose(hip=(56, 55), lean=-8, hand_f=(52, 56), hand_b=(42, 60), foot_f=(80, 58), foot_b=(54, 84),
             foot_f_angle=-18, face="shout", impact=1, spark=1, scarf_phase=1.6),
        Pose(hip=(56, 58), lean=-2, hand_f=(58, 58), hand_b=(44, 60), foot_f=(73, 66), foot_b=(52, 84),
             foot_f_angle=-6, face="strain", scarf_phase=2.4),
    ]
    return p[i]


def hurt_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(53, 62), lean=-10, head_shift=(-1, 1), hand_f=(60, 52), hand_b=(46, 56),
             foot_f=(61, 88), foot_b=(46, 88), face="pain", scarf_phase=1.0),
        Pose(hip=(52, 63), lean=-16, head_shift=(-2, 1), hand_f=(58, 48), hand_b=(44, 52),
             foot_f=(60, 88), foot_b=(45, 88), face="pain", scarf_phase=2.0),
    ]
    return p[i]


def fall_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(52, 64), lean=-34, head_shift=(-1, 1), hand_f=(66, 46), hand_b=(44, 48),
             foot_f=(63, 80), foot_b=(46, 82), face="pain", scarf_phase=1.2),
        Pose(hip=(49, 69), lean=-62, head_shift=(-1, 2), hand_f=(66, 54), hand_b=(42, 52),
             foot_f=(70, 76), foot_b=(52, 80), face="pain", scarf_phase=2.2),
        Pose(face="pain", lying=1),
        Pose(face="pain", lying=1),
    ]
    return p[i]


def getup_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(face="pain", lying=1),
        Pose(hip=(52, 72), lean=-52, head_shift=(-1, 1), hand_f=(64, 66), hand_b=(44, 62),
             foot_f=(66, 82), foot_b=(52, 84), face="strain", scarf_phase=1.3),
        Pose(hip=(52, 70), lean=-30, head_shift=(-1, 1), hand_f=(66, 68), hand_b=(44, 62),
             foot_f=(64, 86), foot_b=(50, 88), face="strain", scarf_phase=2.0),
        Pose(hip=(56, 64), lean=10, hand_f=(62, 62), hand_b=(48, 62), foot_f=(62, 88), foot_b=(49, 88),
             face="strain", scarf_phase=2.7),
    ]
    return p[i]


def victory_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(56, 60), lean=-2, hand_f=(64, 36), hand_b=(48, 48), foot_f=(64, 88), foot_b=(49, 88),
             face="shout", spark=2, scarf_phase=1.0),
        Pose(hip=(56, 61), lean=-1, hand_f=(66, 33), hand_b=(49, 50), foot_f=(64, 88), foot_b=(49, 88),
             face="shout", spark=1, scarf_phase=1.8),
        Pose(hip=(56, 60), lean=-2, hand_f=(64, 35), hand_b=(47, 48), foot_f=(64, 88), foot_b=(49, 88),
             face="strain", spark=2, scarf_phase=2.6),
        Pose(hip=(56, 61), lean=0, hand_f=(66, 34), hand_b=(49, 49), foot_f=(63, 88), foot_b=(49, 88),
             face="neutral", scarf_phase=3.4),
    ]
    return p[i]


# ---------------------------------------------------------------------------
# Enemy poses (RIVET uses the same rig, no scarf, helmet, pipe)
# ---------------------------------------------------------------------------

def enemy_idle_pose(i: int, look: Look) -> Pose:
    bob = (0, 0, 1, 1)[i % 4]
    return Pose(
        hip=(56, 61 - bob), lean=4, hand_f=(57, 60), hand_b=(48, 64),
        foot_f=(64, 88), foot_b=(48, 88), face="neutral",
        pipe_angle=-128 + i, scarf_phase=0,
    )


def enemy_walk_pose(i: int, look: Look) -> Pose:
    p = i / 6
    ff = foot_cycle(p, stride=11, lift=5)
    fb = foot_cycle(p + 0.5, stride=11, lift=5)
    hip_y = 61 - 0.8 * math.cos(4 * math.pi * p)
    return Pose(
        hip=(56, hip_y), lean=8,
        hand_f=(58, 61), hand_b=(47, 64),
        foot_f=ff, foot_b=fb, face="neutral",
        pipe_angle=-125, scarf_phase=0,
    )


def enemy_attack_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(55, 62), lean=-4, hand_f=(48, 55), hand_b=(44, 62), foot_f=(62, 88), foot_b=(48, 88),
             face="strain", pipe_angle=-150),
        Pose(hip=(55, 61), lean=-8, hand_f=(42, 48), hand_b=(40, 60), foot_f=(62, 88), foot_b=(48, 88),
             face="shout", pipe_angle=-170),
        Pose(hip=(57, 61), lean=12, hand_f=(72, 54), hand_b=(44, 58), foot_f=(68, 88), foot_b=(48, 88),
             face="shout", pipe_angle=-8, impact=1),
        Pose(hip=(57, 61), lean=14, hand_f=(74, 58), hand_b=(43, 58), foot_f=(68, 88), foot_b=(48, 88),
             face="shout", pipe_angle=8, impact=1),
        Pose(hip=(56, 62), lean=6, hand_f=(60, 62), hand_b=(47, 63), foot_f=(64, 88), foot_b=(48, 88),
             face="strain", pipe_angle=-90),
    ]
    return p[i]


def enemy_hurt_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(54, 62), lean=-8, hand_f=(60, 54), hand_b=(46, 56), foot_f=(62, 88), foot_b=(47, 88),
             face="pain", pipe_angle=-60),
        Pose(hip=(53, 63), lean=-14, hand_f=(58, 50), hand_b=(44, 54), foot_f=(61, 88), foot_b=(46, 88),
             face="pain", pipe_angle=-40),
    ]
    return p[i]


def enemy_fall_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(hip=(52, 64), lean=-30, hand_f=(64, 50), hand_b=(44, 50), foot_f=(62, 80), foot_b=(46, 82),
             face="pain", pipe_angle=-30),
        Pose(hip=(49, 69), lean=-58, hand_f=(66, 58), hand_b=(42, 54), foot_f=(69, 76), foot_b=(52, 80),
             face="pain", pipe_angle=-20),
        Pose(face="pain", lying=1, pipe_angle=-6),
        Pose(face="pain", lying=1, pipe_angle=0),
    ]
    return p[i]


def enemy_getup_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(face="pain", lying=1, pipe_angle=0),
        Pose(hip=(52, 72), lean=-50, hand_f=(64, 66), hand_b=(44, 62), foot_f=(66, 82), foot_b=(52, 84),
             face="strain", pipe_angle=-20),
        Pose(hip=(53, 70), lean=-26, hand_f=(64, 68), hand_b=(44, 62), foot_f=(64, 86), foot_b=(50, 88),
             face="strain", pipe_angle=-60),
        Pose(hip=(56, 64), lean=8, hand_f=(60, 62), hand_b=(48, 62), foot_f=(62, 88), foot_b=(49, 88),
             face="strain", pipe_angle=-100),
    ]
    return p[i]


def enemy_defeated_pose(i: int, look: Look) -> Pose:
    p = [
        Pose(face="pain", lying=1, pipe_angle=-6),
        Pose(face="pain", lying=1, pipe_angle=0),
    ]
    return p[i]


LOOKS = {
    "volt": Look(bulk=0, helmet=False, scarf=True, weapon=False, gauntlets=True, hair="spikes"),
    "rivet": Look(bulk=2, helmet=True, scarf=False, weapon=True, gauntlets=False, hair="bald"),
}


def palette_for(who: str, elite=False) -> Palette:
    if who == "volt":
        return Palette()
    p = Palette(
        skin=C(196, 138, 98), skin_d=C(150, 96, 64), skin_h=C(224, 172, 128),
        jacket=C(146, 62, 44), jacket_d=C(96, 38, 28), jacket_h=C(196, 94, 62),
        jacket_in=C(54, 22, 20),
        pants=C(52, 50, 58), pants_d=C(34, 33, 40), pants_h=C(76, 74, 84),
        boot=C(30, 27, 32), boot_h=C(86, 78, 78), sole=C(110, 100, 86),
        copper=C(128, 80, 46), copper_d=C(80, 48, 28), copper_h=C(176, 118, 70),
        glow=C(255, 168, 64), glow_d=C(196, 96, 28),
        scarf=C(60, 60, 66), scarf_h=C(100, 100, 110),
        metal=C(112, 124, 132), metal_h=C(168, 180, 186), metal_d=C(60, 68, 74),
        rim=C(255, 168, 84),
    )
    if elite:
        p.jacket = C(84, 84, 96)
        p.jacket_d = C(52, 52, 64)
        p.jacket_h = C(142, 142, 154)
        p.glow = C(255, 92, 72)
        p.rim = C(255, 104, 88)
        p.metal = C(128, 128, 138)
        p.metal_h = C(190, 190, 200)
    return p


def draw_helmet(f: Frame, center, pal: Palette, elite=False):
    cx, cy = center
    f.dot((cx, cy), pal.metal_d, 7, OUT)
    f.poly([(cx - 6, cy - 3), (cx + 6, cy - 3), (cx + 7, cy + 2), (cx + 4, cy + 6),
            (cx - 5, cy + 6), (cx - 7, cy + 1)], pal.metal, OUT)
    f.line([(cx - 4, cy + 1), (cx + 5, cy + 1)], pal.metal_h, 1)
    f.box(cx + 1, cy - 1, cx + 5, cy + 1, C(20, 16, 20))
    f.line([(cx + 2, cy), (cx + 4, cy)], pal.glow, 1)
    f.line([(cx - 6, cy - 2), (cx - 4, cy - 4)], pal.metal_h, 1)
    # breathing vents
    for k in (-2, 0, 2):
        f.line([(cx + 2, cy + 3 + k // 2), (cx + 5, cy + 3 + k // 2)], pal.metal_d, 1)
    # rivets
    f.dot((cx - 3, cy + 4), pal.metal_h, 0)
    f.dot((cx + 3, cy + 4), pal.metal_h, 0)
    if elite:
        f.line([(cx - 1, cy - 6), (cx + 1, cy - 9), (cx + 3, cy - 6)], pal.glow, 1)


def draw_lying(pose: Pose, pal: Palette, look: Look) -> Image.Image:
    """A dedicated floor pose.  Reusing the standing skeleton at -90 degrees
    produced unreadable piles, so the lying body is authored explicitly:
    pelvis at x=60, torso laid to the left, head at the left end, boots right."""
    f = Frame()
    pelvis = (60, 84)
    torso(f, pelvis, -90, pal, look)
    # legs: knees up, boots towards the right
    leg(f, (64, 84), (84, 88), pal, front=True, bulky=look.bulk > 0, foot_angle=90)
    leg(f, (58, 82), (78, 80), pal, front=False, bulky=look.bulk > 0, foot_angle=70)
    # head at the left end of the torso, neck pointing back to the shoulders
    head_c = (30, 82)
    head(f, head_c, pal, look, face="pain", axis=(1, 0.12))
    # splayed arm with the gauntlet resting on the ground
    arm(f, (44, 82), (50, 72), pal, look, front=True, spark=0)
    if look.weapon:
        f.line([(50, 72), (34, 66)], pal.metal_d, 3)
        f.line([(50, 72), (34, 66)], pal.metal, 1)
    if look.scarf:
        scarf(f, (36, 86), pal, 1.4, lift=0)
    return pad(f.img)


def render(who: str, pose: Pose, elite=False) -> Image.Image:
    pal = palette_for(who, elite)
    look = LOOKS[who]
    img = draw_lying(pose, pal, look) if pose.lying else draw_character(pose, pal, look)
    if look.helmet and pose.lying:
        f = Frame()
        f.img = img
        f.d = ImageDraw.Draw(img)
        draw_helmet(f, (30 + CONTENT_X, 82), pal, elite)
    if look.helmet and not pose.lying:
        # helmet replaces the hair/face layer; draw it on top at the head position
        up = rot((0, -1), pose.lean)
        pelvis = pose.hip
        shoulder = add(pelvis, (up[0] * 24, up[1] * 24))
        neck = add(shoulder, (up[0] * 4, up[1] * 4))
        head_c = add(neck, (up[0] * 8 + pose.head_shift[0], up[1] * 8 + pose.head_shift[1]))
        f = Frame()
        f.img = img
        f.d = ImageDraw.Draw(img)
        draw_helmet(f, (head_c[0] + CONTENT_X, head_c[1]), pal, elite)
    if pose.lying:
        # Lift the floor pose 2 px so the boots never touch the canvas edge
        # (the QA gate rejects artwork at the border; a lying body is the only
        # pose that naturally reaches it).
        lifted = Image.new('RGBA', img.size, (0, 0, 0, 0))
        lifted.alpha_composite(img, (0, -2))
        img = lifted
    return img
