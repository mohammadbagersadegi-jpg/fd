#!/usr/bin/env python3
"""Extract the stage-1 palette / scene descriptor tables from the listing.

Outputs ``reports/stage01-palette-descriptors.json``.  Only indices and
selection data are emitted — no colour values are interpreted, because the
mega-drive 9-bit RGB entries are not needed for the reconstruction and the
listing order says nothing about which palette id means which colour name.

Usage:
    python3 tools/research/stage01_tables.py --listing "$SOR_LISTING"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

from listing import read_listing  # noqa: E402

LABEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")
UNRESOLVED: list[str] = []
NUM = re.compile(r"^\$([0-9A-Fa-f]+)$")
DEC = re.compile(r"^-?\d+$")

TABLE_START = "off_1C1C4"
TABLE_END = "off_1C400"
ANCHORS = {"off_1C1C4": 0x1C1C4, "Pal_Alt_Boss": 0x1C3A8, "Pal_Alt_Enemy": 0x1FACC}
REGIONS = [("off_1C1C4", "Pal_Antonio_Blue"), ("Pal_Alt_Boss", "off_1C400"),
           ("Pal_Alt_Enemy", "Pal_Galsia_Blue")]
BOSS_TABLE = "Pal_Alt_Boss"
ENEMY_TABLE = "Pal_Alt_Enemy"


def eval_operand(text: str, labels: dict[str, int], pc: int) -> int:
    text = text.strip()
    minus = text.split("-")
    value = 0
    for i, part in enumerate(minus):
        part = part.strip()
        if NUM.match(part):
            term = int(NUM.match(part).group(1), 16)
        elif DEC.match(part):
            term = int(part) & 0xFFFFFFFF
        elif part in labels:
            term = labels[part]
        else:
            # bare label defined outside the parsed region (palette payload);
            # record it and store zero so later offsets stay aligned.
            UNRESOLVED.append(part)
            term = 0
        value = value - term if i else term
    return value


def read_table(lines, start_label: str, end_label: str) -> tuple[dict, dict]:
    """Return (labels, bytes) for the data between two labels."""
    labels: dict[str, int] = {}
    start = None
    for number, line in enumerate(lines, 1):
        m = LABEL.match(line)
        if m:
            name, rest = m.group(1), m.group(2)
            # labels in this region are absolute; the listing prints them in a
            # separate equ block, so re-derive addresses from the first label.
            if start is None:
                if name == start_label:
                    start = number
            elif name == end_label:
                return labels, {}
    raise ValueError(f"{start_label} not found")


def parse_region(lines, start_label: str = TABLE_START,
                 end_label: str = TABLE_END) -> dict:
    """Parse every dc directive between two labels.

    Addresses are tracked by keeping a cursor: the first label in the region is
    anchored at the address encoded in its name (``off_1C1C4`` -> 0x1C1C4).
    """
    first = None
    end_address = None
    region: list[tuple[int, str]] = []
    for number, line in enumerate(lines, 1):
        if re.match(rf"^{start_label}:", line) and first is None:
            first = number
        if first is None:
            continue
        if re.match(rf"^{end_label}:", line):
            break
        region.append((number, line))
    if first is None:
        raise ValueError(f"{start_label} not found")

    # Pass 1: walk the directives to learn every label address.  Operand values
    # are irrelevant for sizing: the directive name alone fixes the width.
    cursor = ANCHORS[start_label]
    labels: dict[str, int] = {}
    directives: list[dict] = []
    plan: list[tuple[int, list[str], str, int]] = []
    for number, line in region:
        body = line.split(";", 1)[0].rstrip()
        if not body.strip():
            continue
        m = LABEL.match(body)
        if m:
            labels[m.group(1)] = cursor
            directives.append({"line": number, "label": m.group(1), "address": cursor})
            body = m.group(2).strip()
        else:
            directives.append({"line": number, "label": None, "address": cursor})
        if not body:
            continue
        parts = body.split(None, 1)
        if not parts[0].startswith("dc."):
            continue
        size = {"dc.b": 1, "dc.w": 2, "dc.l": 4}[parts[0]]
        operands = [p.strip() for p in parts[1].split(",") if p.strip()]
        plan.append((number, operands, parts[0], size))
        cursor += size * len(operands)
    labels.setdefault(end_label, cursor)   # end label sits at the region end

    # Pass 2: evaluate with the complete label table.
    memory: dict[int, int] = {}
    cursor = ANCHORS[start_label]
    for number, operands, kind, size in plan:
        for text in operands:
            value = eval_operand(text, labels, cursor) & ((1 << (8 * size)) - 1)
            for byte_index in range(size):
                memory[cursor + byte_index] = (value >> (8 * (size - 1 - byte_index))) & 0xFF
            cursor += size

    return {"labels": labels, "memory": memory, "directives": directives,
            "start": ANCHORS[start_label], "end": cursor}


def guess_label(name: str) -> str:
    for prefix in ("dword_", "word_", "byte_", "off_"):
        if name.startswith(prefix):
            return prefix.rstrip("_")
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listing", default=os.environ.get("SOR_LISTING"))
    parser.add_argument("--out", default=str(ROOT / "reports"))
    args = parser.parse_args()
    if not args.listing:
        print("error: --listing or SOR_LISTING is required", file=sys.stderr)
        return 2
    listing = Path(args.listing).expanduser()
    lines = read_listing(listing)
    regions = [parse_region(lines, a, b) for a, b in REGIONS]
    labels: dict[str, int] = {}
    memory: dict[int, int] = {}
    for region in regions:
        labels.update(region["labels"])
        memory.update(region["memory"])
    region = regions[0]

    def word(address: int) -> int:
        return (memory[address] << 8) | memory[address + 1]

    def long_(address: int) -> int:
        if not all(address + i in memory for i in range(4)):
            return -1          # pointer leaves the parsed table region
        return int.from_bytes(bytes(memory[address + i] for i in range(4)), "big")

    def blob(address: int, length: int) -> str:
        return " ".join(f"{memory[address + i]:02x}" for i in range(length))

    roots = [word(region["start"] + 2 * i) + region["start"] for i in range(8)]
    rounds = []
    for index, root in enumerate(roots):
        slots = []
        # the offset table length is inferred from the distance to the next
        # root (or to off_1C378 for the last round)
        next_root = roots[index + 1] if index + 1 < len(roots) else labels["off_1C378"]
        # the offset list ends where the first entry's data begins
        slot_count = word(root) // 2
        for slot in range(slot_count):
            target = word(root + 2 * slot) + root
            entry = {"slot": slot, "offset": target,
                     "offset_hex": f"0x{target:04X}"}
            if slot == 0:
                entry.update({
                    "cursor": f"0x{long_(target):08X}",
                    "geometry_index": word(target + 4),
                    "bytes": blob(target + 6, 6),
                    "role": "level start: ELC cursor + geometry + palettes",
                })
                descriptor = target + 6
            else:
                entry.update({
                    "bytes": blob(target, 6),
                    "role": "scene transition palette descriptor",
                })
                descriptor = target
            b = [memory[descriptor + i] for i in range(6)]
            entry["descriptor"] = {
                "pal_correct": [b[0], b[1], b[2], b[3]],
                "selector_byte": b[4],
                "boss_table": bool(b[4] & 0x80),
                "enemy_palette_index": ((b[4] >> 4) & 0x7) + 8 if (b[4] >> 4) & 0xF else None,
                "last_byte_low_nibble": b[5] & 0x0F,
            }
            slots.append(entry)
        rounds.append({
            "round": index + 1,
            "root": root,
            "root_hex": f"0x{root:04X}",
            "slots": len(slots),
            "bytes": next_root - root,
            "entries": slots,
        })

    boss = []
    boss_base = labels[BOSS_TABLE]
    for i in range(6):
        entry = boss_base + i * 6
        boss.append({
            "index": i,
            "descriptor_word": f"0x{word(entry):04X}",
            "palette_list": f"0x{long_(entry + 2):04X}",
            "target_label": next((n for n, a in labels.items() if a == long_(entry + 2)), None),
            "palettes": [
                (f"0x{long_(long_(entry + 2) + 4 * i):04X}"
                 if long_(entry + 2) > 0 and long_(long_(entry + 2) + 4 * i) > 0 else None)
                for i in range(3)
            ],
        })

    enemy_base = labels[ENEMY_TABLE]
    enemy = [{
        "index": i,
        "status": "UNKNOWN",
        "note": "relative word not extracted; see listing Pal_Alt_Enemy (line 49071)",
    } for i in range(12)]

    payload = {
        "schema": "stage01-palette-descriptors/1",
        "target": "Streets of Rage (JUE) (REV 00)",
        "listing": {"file": listing.name,
                    "sha256": hashlib.sha256(listing.read_bytes()).hexdigest()},
        "rounds": rounds,
        "boss_palette_table": {"label": BOSS_TABLE, "address": f"0x{boss_base:04X}",
                               "entry_size": 6, "entries": boss},
        "enemy_palette_table": {
            "label": ENEMY_TABLE, "address": f"0x{enemy_base:04X}",
            "entry_size": 2, "entry_count": 12, "entries": enemy,
            "status": "LOCATED_AND_SIZED / CONTENTS_UNRESOLVED",
            "note": "twelve relative words, each target holding two frame-alternate "
                    "palette pointers; the payload pointers were not extracted",
        },
        "selection_logic": {
            "routine": "Update_Enemy_Pal (listing 1865)",
            "inputs": "6-byte descriptor consumed by sub_576 / EnemySpawn_Scene / Load_Enemy_Into_RAM",
            "pal_correct": "bytes 0-3 -> $FFFFFA60..$FFFFFA63",
            "selector": "byte 4: bit 7 selects Pal_Alt_Boss, high nibble (+8) -> Pal_ID_Enemy, low nibble selects the alternate",
            "last_byte": "byte 5 low nibble -> $FFFFFA6A",
            "boss_entry_size": "6 bytes per entry = word target descriptor + long palette-list pointer",
            "enemy_entry_size": "12 relative words; each target holds two frame-alternate palette pointers",
        },
        "notes": [
            "No RGB values are emitted; palette data is analysed as indices only.",
            "The geometry word indexes word_1C1BC: 0 -> stride 1, base $0300; 1 -> stride -1, base $1300.",
        ],
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stage01-palette-descriptors.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"rounds : {len(rounds)} roots, slots " + "/".join(str(r['slots']) for r in rounds))
    print(f"boss   : {len(boss)} entries, enemy table: {len(enemy)} slots (contents unresolved)")
    print(f"wrote  : {out / 'stage01-palette-descriptors.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
