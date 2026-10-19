#!/usr/bin/env python3
"""Regression tests for the round-1 / all-rounds ELC analysis.

Run with:

    python3 tools/research/test_stage01.py

The tests need the decoded streams.  They are looked up in this order:

1. ``analysis/elc/roundN.bin`` (written by ``extract_stage01.py``);
2. decoded on the fly from the listing cloned at ``vendor/sor-dis`` or
   pointed to by ``$SOR_LISTING``;
3. if neither exists the test is skipped with instructions (never silently
   passed).

Every test that touches bytes asserts an exact expectation.  If the parser
ever starts dropping bytes, ``test_tail_is_accounted_for`` and
``test_walk_matches_parse`` fail instead of hiding the loss.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

from elc import parse_stream, walk_stream, segments_cover  # noqa: E402

SIZES = {1: 0x1C0, 2: 0x280, 3: 0x240, 4: 0x240, 5: 800, 6: 0x2E0, 7: 0x1E0, 8: 0x380}
BLOCKS = {1: 4, 2: 4, 3: 4, 4: 4, 5: 6, 6: 6, 7: 5, 8: 6}
TAIL_BYTES = {1: 24, 2: 42, 3: 70, 4: 54, 5: 46, 6: 74, 7: 20, 8: 158}
ROUND1_BLOCK_ENDS = [0x04C, 0x0BE, 0x13C, 0x1A8]
ROUND1_TAIL_HEX = "00 10 56 00 04 00 10 00 00 10 d6 01 05 00 10 01 00 99 00 02 99 00 6a 00"
ROUND1_BOOTHS = [2016, 2192, 2472, 2920, 2960, 3000, 3672]
TAIL_FIRST_PAIR = {
    1: (16, 0x56),
    2: (16, 0x55),
    3: (16, 0x30),
    4: (16, 0x57),
    5: (16, 0x58),
    6: (16, 0x55),
    8: (1, 0x33),
}
# Published one-player census (RuiNelson autoplay/CLAUDE.md).  Enemy types only.
EXPECTED_1P = {
    1: {0x22: 17, 0x21: 6, 0x20: 2, 0x23: 1, 0x24: 3, 0x25: 2, 0x26: 4, 0x27: 0},
    2: {0x22: 16, 0x21: 11, 0x20: 4, 0x23: 1, 0x24: 6, 0x25: 4, 0x26: 3, 0x27: 3},
    3: {0x22: 8, 0x21: 5, 0x20: 4, 0x23: 2, 0x24: 5, 0x25: 3, 0x2A: 1, 0x26: 8, 0x27: 0},
    4: {0x22: 8, 0x21: 7, 0x20: 8, 0x23: 2, 0x24: 16, 0x25: 3, 0x26: 5, 0x27: 1},
    5: {0x22: 26, 0x21: 3, 0x20: 6, 0x23: 3, 0x24: 6, 0x25: 12, 0x2A: 2, 0x26: 7, 0x27: 6},
    6: {0x22: 10, 0x21: 8, 0x20: 4, 0x23: 2, 0x24: 15, 0x25: 7, 0x26: 9, 0x27: 3},
    7: {0x22: 9, 0x21: 4, 0x20: 3, 0x23: 1, 0x24: 15, 0x25: 15, 0x26: 5, 0x27: 0},
    8: {0x22: 6, 0x21: 8, 0x20: 3, 0x23: 2, 0x24: 20, 0x25: 12, 0x2A: 1, 0x26: 5, 0x27: 2},
}


def listing_path() -> Path | None:
    env = os.environ.get("SOR_LISTING")
    candidates = [Path(env).expanduser()] if env else []
    candidates.append(ROOT / "vendor/sor-dis/Assemblies/Streets of Rage (JUE) (REV 00) [!].asm")
    for path in candidates:
        if path.exists():
            return path
    return None


def load_stream(round_no: int) -> bytes:
    cache = ROOT / "analysis" / "elc" / f"round{round_no}.bin"
    if cache.exists():
        return cache.read_bytes()
    listing = listing_path()
    if listing is None:
        raise unittest.SkipTest(
            "no decoded stream and no listing; run extract_stage01.py or clone "
            "gsaurus/sor-disassemblies into vendor/sor-dis"
        )
    from listing import read_listing, extract_dc_b
    from nemesis import decompress

    labels = {1: "byte_1B046", 2: "byte_1B1D8", 3: "byte_1B3F4", 4: "byte_1B5D0",
              5: "byte_1B7DE", 6: "byte_1BA8C", 7: "byte_1BD12", 8: "byte_1BEBE"}
    data = decompress(extract_dc_b(read_listing(listing), labels[round_no]).data)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(data)
    return data


class StreamTests(unittest.TestCase):
    def test_decoded_sizes(self):
        for round_no, size in SIZES.items():
            with self.subTest(round=round_no):
                self.assertEqual(len(load_stream(round_no)), size)

    def test_block_boundaries(self):
        for round_no, blocks in BLOCKS.items():
            with self.subTest(round=round_no):
                _, parsed_blocks, tail = parse_stream(load_stream(round_no), max_blocks=blocks)
                self.assertEqual(len(parsed_blocks), blocks)
                self.assertEqual(tail, parsed_blocks[-1]["end"])

    def test_walk_matches_parse(self):
        for round_no, blocks in BLOCKS.items():
            with self.subTest(round=round_no):
                data = load_stream(round_no)
                records, parsed, tail = parse_stream(data, max_blocks=blocks)
                segments, walk_tail = walk_stream(data, max_blocks=blocks)
                self.assertEqual(tail, walk_tail)
                self.assertTrue(segments_cover(segments, 0, tail))
                block_ends = {b["block"]: b["end"] for b in parsed}
                for block_no, end in block_ends.items():
                    self.assertEqual(
                        max(s["end"] for s in segments if s["block"] == block_no), end
                    )
                batch = sum(1 for s in segments if s["kind"] == "batch_record")
                timed = sum(1 for s in segments if s["kind"] == "timed_record")
                deferred = sum(1 for s in segments if s["kind"] == "deferred_record")
                self.assertEqual(batch, sum(1 for r in records if r.kind == "batch"))
                self.assertEqual(timed, sum(1 for r in records if r.kind == "timed"))
                self.assertEqual(deferred, sum(1 for r in records if r.kind == "deferred"))

    def test_sentinels_and_lengths(self):
        for round_no, blocks in BLOCKS.items():
            data = load_stream(round_no)
            segments, _ = walk_stream(data, max_blocks=blocks)
            for seg in segments:
                if seg["kind"] == "timed_end":
                    self.assertEqual(seg["value"], 0x0099)
                if seg["kind"] == "deferred_end":
                    self.assertEqual(seg["value"], "9900")
                if seg["kind"] == "deferred_length":
                    start = seg["end"]
                    end = start + seg["value"]
                    self.assertTrue(
                        any(s["kind"] == "deferred_end" and s["end"] == end for s in segments),
                        f"round {round_no} block {seg['block']}: deferred length "
                        f"{seg['value']:#x} does not land on a $99 terminator",
                    )

    def test_tail_is_accounted_for(self):
        for round_no, size in SIZES.items():
            with self.subTest(round=round_no):
                data = load_stream(round_no)
                _, _, tail = parse_stream(data, max_blocks=BLOCKS[round_no])
                self.assertEqual(len(data) - tail, TAIL_BYTES[round_no])
                # The tail must be reported, never swallowed.
                self.assertGreater(tail, 0)
                self.assertLess(tail, size)

    def test_tail_offsets_and_hashes(self):
        expected = {
            1: (0x1A8, 24), 2: (0x256, 42), 3: (0x1FA, 70), 4: (0x20A, 54),
            5: (0x2F2, 46), 6: (0x296, 74), 7: (0x1CC, 20), 8: (0x2E2, 158),
        }
        for round_no, (offset, length) in expected.items():
            with self.subTest(round=round_no):
                data = load_stream(round_no)
                _, _, tail = parse_stream(data, max_blocks=BLOCKS[round_no])
                self.assertEqual(tail, offset)
                self.assertEqual(len(data) - tail, length)

    def test_tail_hex_round1_and_round2(self):
        data = load_stream(1)
        _, _, tail = parse_stream(data, max_blocks=4)
        self.assertEqual(data[tail:].hex(" "), ROUND1_TAIL_HEX)
        data2 = load_stream(2)
        _, _, tail2 = parse_stream(data2, max_blocks=4)
        self.assertEqual(
            data2[tail2:].hex(" "),
            "00 10 55 00 08 00 10 00 00 10 d5 01 09 00 10 01 00 20 22 00 39 00 40 00 "
            "00 99 00 0e 22 00 39 00 40 00 20 01 3d 00 61 01 99 00",
        )

    def test_round2_tail_is_complete(self):
        # Round 2 is the only tail that consumes the buffer exactly.
        from elc import parse_tail
        data = load_stream(2)
        _, _, tail = parse_stream(data, max_blocks=4)
        parsed = parse_tail(data, tail)
        self.assertEqual(parsed["leftover_bytes"], 0)
        self.assertEqual(len(parsed["pairs"]), 3)
        self.assertEqual(parsed["pairs"][0]["type"], 0x55)
        self.assertEqual(parsed["pairs"][1]["type"], 0xD5)
        self.assertEqual(parsed["pairs"][1]["side"], "left_edge")
        self.assertEqual(parsed["sections"][0]["length"], 0x0E)
        self.assertEqual(parsed["sections"][0]["status"], "ok")

    def test_round1_tail_leftover_is_reported(self):
        from elc import parse_tail
        data = load_stream(1)
        _, _, tail = parse_stream(data, max_blocks=4)
        parsed = parse_tail(data, tail)
        self.assertEqual(parsed["pairs"][0]["type"], 0x56)
        self.assertEqual(parsed["pairs"][0]["delay"], 16)
        self.assertEqual(parsed["sections"][0]["length"], 2)
        self.assertEqual(parsed["sections"][0]["records"], 0)
        # the two bytes after the empty section must be reported, not dropped
        self.assertEqual(parsed["leftover_bytes"], 2)
        self.assertEqual(parsed["leftover"], "6a 00")

    def test_round1_exact_layout(self):
        data = load_stream(1)
        records, blocks, tail = parse_stream(data, max_blocks=4)
        self.assertEqual([b["end"] for b in blocks], ROUND1_BLOCK_ENDS)
        self.assertEqual(len(records), 59)
        self.assertEqual(
            {k: sum(1 for r in records if r.kind == k) for k in ("batch", "timed", "deferred")},
            {"batch": 38, "timed": 11, "deferred": 10},
        )
        self.assertEqual(data[tail:].hex(" "), ROUND1_TAIL_HEX)

    def test_tail_first_pair(self):
        for round_no, (delay, type_id) in TAIL_FIRST_PAIR.items():
            with self.subTest(round=round_no):
                data = load_stream(round_no)
                _, _, tail = parse_stream(data, max_blocks=BLOCKS[round_no])
                self.assertEqual((data[tail] << 8) | data[tail + 1], delay)
                self.assertEqual(data[tail + 2], type_id)

    def test_truncation_raises(self):
        data = load_stream(1)
        truncated = data[:0x1A7]
        with self.assertRaises(ValueError):
            parse_stream(truncated, max_blocks=4)
        with self.assertRaises(ValueError):
            walk_stream(truncated, max_blocks=4)

    def test_full_parse_raises_on_tail(self):
        # Without max_blocks the parser must walk into the tail and refuse it,
        # rather than silently returning a short record list.
        with self.assertRaises(ValueError):
            parse_stream(load_stream(1))


class CensusTests(unittest.TestCase):
    def test_one_player_census_all_rounds(self):
        for round_no, expected in EXPECTED_1P.items():
            with self.subTest(round=round_no):
                records, _, _ = parse_stream(
                    load_stream(round_no), max_blocks=BLOCKS[round_no]
                )
                got: dict[int, int] = {}
                for rec in records:
                    if rec.two_player_only:
                        continue
                    got[rec.type_id] = got.get(rec.type_id, 0) + 1
                for type_id, count in expected.items():
                    self.assertEqual(
                        got.get(type_id, 0), count,
                        f"round {round_no} type {type_id:#04x}",
                    )

    def test_round1_booth_predictions(self):
        records, _, _ = parse_stream(load_stream(1), max_blocks=4)
        booths = sorted(r.x_world for r in records
                        if r.kind == "batch" and r.type_id == 0x11 and not r.two_player_only)
        self.assertEqual(booths, ROUND1_BOOTHS)
        # Two positions documented by the third-party runtime notes.
        self.assertIn(2016, booths)
        self.assertIn(2920, booths)


class SpawnModelTests(unittest.TestCase):
    def test_column_base_model(self):
        # Base starts at 0x0300 and the *high* byte is incremented between the
        # three Init_Enemy calls, so the base advances 0x100 per column and
        # keeps going across blocks.
        for block in range(1, 5):
            for column in range(3):
                index = 3 * (block - 1) + column
                self.assertEqual(0x0300 + 0x100 * index,
                                 [0x300, 0x400, 0x500, 0x600, 0x700, 0x800,
                                  0x900, 0xA00, 0xB00, 0xC00, 0xD00, 0xE00][index])

    def test_no_record_escapes_its_band(self):
        records, _, _ = parse_stream(load_stream(1), max_blocks=4)
        for rec in records:
            if rec.kind != "batch":
                continue
            base = 0x0300 + 0x100 * rec.column_index
            self.assertEqual(rec.x_world & 0xFF00, base & 0xFF00)
            self.assertEqual(rec.x_world & 0xFF, rec.x_low)


class PaletteTableTests(unittest.TestCase):
    SLOTS = {1: 5, 2: 5, 3: 5, 4: 5, 5: 7, 6: 7, 7: 7, 8: 7}
    ROUND1_DESCRIPTORS = [
        "00 01 02 00 00 03", "00 01 02 00 00 03", "00 01 03 00 00 06",
        "00 01 04 00 10 00", "00 00 00 00 00 00",
    ]

    def setUp(self):
        path = ROOT / "reports/stage01-palette-descriptors.json"
        if not path.exists():
            self.skipTest("palette descriptor table not generated yet")
        self.table = json.loads(path.read_text())

    def test_slot_counts(self):
        for round_data in self.table["rounds"]:
            with self.subTest(round=round_data["round"]):
                self.assertEqual(round_data["slots"], self.SLOTS[round_data["round"]])

    def test_round1_descriptors(self):
        entries = self.table["rounds"][0]["entries"]
        self.assertEqual([e["bytes"] for e in entries], self.ROUND1_DESCRIPTORS)

    def test_boss_table_entries(self):
        entries = self.table["boss_palette_table"]["entries"]
        self.assertEqual(len(entries), 6)
        self.assertEqual(entries[0]["descriptor_word"], "0x551B")
        self.assertEqual(entries[0]["palette_list"], "0x1C3CC")

    def test_enemy_table_topology(self):
        table = self.table["enemy_palette_table"]
        self.assertEqual(table["entry_count"], 12)
        self.assertEqual(table["status"], "LOCATED_AND_SIZED / CONTENTS_UNRESOLVED")


class ArtifactTests(unittest.TestCase):
    def test_dossier_json_is_current(self):
        path = ROOT / "reports/stage01-elc-records.json"
        if not path.exists():
            self.skipTest("dossier not generated yet")
        dossier = json.loads(path.read_text())
        data = load_stream(1)
        digest = hashlib.sha256(data).hexdigest()
        self.assertEqual(dossier["rounds"]["1"]["stream_sha256"], digest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
