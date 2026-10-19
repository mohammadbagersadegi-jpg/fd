#!/usr/bin/env python3
"""Compose config/stages.json — the eight-stage campaign.

Stage 1 is the hand-tuned vertical slice from config/stage.json (unchanged
layout, same three waves).  Stages 2-8 are generated from a small, explicit
table so wave counts, enemy mixes and boss placement stay auditable: every
number in the output comes from this file, not from a random generator.

World width grows by 100 px per stage; each stage keeps the same lane band and
pickup rules.  Difficulty ramps through two multipliers read by the runtime
(`enemyHealthMul`, `enemyDamageMul`) and through the enemy mix.

Usage:
    python3 tools/stage_pipeline/make_stages.py [--check]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT = CONFIG / "stages.json"

# (title, subtitle, theme tint, wave count, regular enemies per wave, mix bias)
STAGES = [
    ("RAIN DISTRICT", "STAGE 1 - BLOCK 07", "rgba(80,170,255,0.05)", 3, 3, 0),
    ("SOUTH DOCKS", "STAGE 2 - PIER NINE", "rgba(255,170,90,0.06)", 3, 3, 1),
    ("NEON MARKET", "STAGE 3 - ARCADE ROW", "rgba(255,90,200,0.06)", 3, 3, 2),
    ("STEEL YARD", "STAGE 4 - FOUNDRY", "rgba(255,210,120,0.05)", 4, 3, 1),
    ("SKYLINE TRANSIT", "STAGE 5 - PLATFORM B", "rgba(120,255,220,0.05)", 4, 4, 2),
    ("RED SECTOR", "STAGE 6 - CHECKPOINT", "rgba(255,90,90,0.07)", 4, 4, 3),
    ("TOWER BASE", "STAGE 7 - LOBBY", "rgba(150,150,255,0.06)", 4, 4, 3),
    ("MR. X TOWER", "STAGE 8 - PENTHOUSE", "rgba(255,60,60,0.08)", 4, 4, 4),
]

# Enemy mix per bias.  `runner` and `overlord` are the two added archetypes;
# every entry maps to an existing sprite sheet (rivet / rivet_elite).
MIX = {
    0: ["rivet", "rivet", "rivet"],
    1: ["rivet", "runner", "rivet"],
    2: ["rivet", "runner", "rivet_elite"],
    3: ["rivet_elite", "runner", "rivet", "rivet_elite"],
    4: ["rivet_elite", "runner", "rivet_elite", "runner"],
}

LANES = [212, 238, 224, 246, 218, 232, 208, 240]
PROP_TYPES = ["crate", "trash", "barrel", "crate"]


def clamp_z(z: int, lane_min: int, lane_max: int) -> int:
    return max(lane_min + 4, min(lane_max - 4, z))


def build_stage(index: int, spec, base: dict) -> dict:
    title, subtitle, tint, wave_count, per_wave, bias = spec
    world = 1800 + 100 * index
    lane_min, lane_max = base["laneMin"], base["laneMax"]
    time_limit = 99 + 5 * index

    if index == 0:
        # Stage 1 keeps the hand-tuned slice exactly as shipped.
        stage = json.loads(json.dumps(base))
        stage.update({"index": 0, "theme": tint, "timeLimitSeconds": time_limit,
                      "enemyHealthMul": 1.0, "enemyDamageMul": 1.0})
        return stage

    waves = []
    span = world - 520
    for w in range(wave_count):
        trigger = int(240 + span * (w / max(1, wave_count - 1))) if wave_count > 1 else 240
        final = w == wave_count - 1
        enemies = []
        count = per_wave + (1 if index >= 5 and w == wave_count - 2 else 0)
        for k in range(count):
            kind = MIX[bias][k % len(MIX[bias])]
            x_off = 30 + (k % 3) * 34 + (w % 2) * 10
            z = clamp_z(LANES[(k + w) % len(LANES)], lane_min, lane_max)
            enemies.append({
                "type": kind,
                "spawnSide": "right" if k % 2 == 0 else "left",
                "spawnOffset": x_off,
                "spawnZ": z,
                "delay": 0 if k == 0 else 45 + 35 * k,
            })
        if final:
            # Boss wave: one overlord plus two escorts, banner announces it.
            enemies = [
                {"type": "overlord", "spawnSide": "right", "spawnOffset": 60,
                 "spawnZ": clamp_z(226, lane_min, lane_max), "delay": 30},
                {"type": "rivet_elite", "spawnSide": "left", "spawnOffset": 40,
                 "spawnZ": clamp_z(214, lane_min, lane_max), "delay": 90},
                {"type": "runner", "spawnSide": "right", "spawnOffset": 96,
                 "spawnZ": clamp_z(242, lane_min, lane_max), "delay": 140},
            ]
        waves.append({
            "id": w + 1,
            "triggerX": max(220, min(trigger, world - 120)),
            "lockCamera": True,
            "banner": "BOSS" if final else f"WAVE {w + 1}",
            "enemies": enemies,
        })

    props = []
    for i in range(5):
        px = int(world * (0.22 + 0.14 * i))
        props.append({
            "id": f"prop_{index}_{i}",
            "type": PROP_TYPES[i % len(PROP_TYPES)],
            "x": min(world - 120, px),
            "z": clamp_z(LANES[i % len(LANES)], lane_min, lane_max),
            "hp": 2 if PROP_TYPES[i % len(PROP_TYPES)] == "crate" else 1,
            "drop": "health" if i % 3 == 1 else "score",
        })

    return {
        "$schema_version": "1.0",
        "index": index,
        "id": f"stage_{index + 1:02d}",
        "title": title,
        "subtitle": subtitle,
        "theme": tint,
        "timeLimitSeconds": time_limit,
        "enemyHealthMul": round(1.0 + 0.10 * index, 2),
        "enemyDamageMul": round(1.0 + 0.06 * index, 2),
        "worldWidth": world,
        "laneMin": lane_min,
        "laneMax": lane_max,
        "startX": 80,
        "startZ": 226,
        "music": base.get("music", "neon-rain-loop"),
        "banners": {"title": title, "wave": "WAVE", "clear": "STAGE CLEAR", "go": "GO"},
        "waves": waves,
        "props": props,
        "pickups": json.loads(json.dumps(base["pickups"])),
        "finishLineX": world - 40,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="fail if config/stages.json is out of date")
    args = ap.parse_args()

    base = json.loads((CONFIG / "stage.json").read_text(encoding="utf-8"))
    stages = [build_stage(i, spec, base) for i, spec in enumerate(STAGES)]
    payload = {"$schema_version": "1.0", "stages": stages}
    text = json.dumps(payload, indent=2) + "\n"

    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print("config/stages.json is stale — rerun without --check")
            return 1
        print("config/stages.json is up to date")
        return 0

    OUT.write_text(text, encoding="utf-8")
    enemies = [sum(len(w["enemies"]) for w in s["waves"]) for s in stages]
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  stages   : {len(stages)}")
    print(f"  world px : {[s['worldWidth'] for s in stages]}")
    print(f"  waves    : {[len(s['waves']) for s in stages]}")
    print(f"  enemies  : {enemies} (total {sum(enemies)})")
    print(f"  bosses   : {sum(1 for s in stages for w in s['waves'] for e in w['enemies'] if e['type'] == 'overlord')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
