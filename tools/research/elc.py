"""Parse the per-round enemy load-cue (ELC) stream.

Format (see reports/reference-stage-01.md and game-engine-and-levels.md §5):

  block := batch batch batch timed_list length_prefixed_section
  batch := word count_minus_one (negative = empty) + (count+1) * 6-byte record
  timed := (word delay, 6-byte record)* word $0099
  deferred := word byte_length, byte_length bytes of 6-byte records, $99,$00

Record layout: type, param40, param41, param49, byte4, byte5.

For batch records byte4 is the X low byte and byte5 goes to object +$15.
For timed/deferred records sub_C60 copies byte4 to +$15 and uses **byte5**
as the edge selector: 0 -> spawn at cam_x + $148 (right edge), non-zero ->
cam_x - 8 (left edge).  `side` below implements that rule.

Batch records place X at (base & 0xFF00) | x_low.  `add.b d2,($FFFFFB12).w`
adds to the *high* byte of the base (68000 big-endian: the byte at the word
address is the high byte), so each of the three columns starts 0x100 further
right and the base keeps advancing across blocks.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class Record:
    kind: str          # "batch" | "timed" | "deferred"
    block: int
    column: int | None
    offset: int
    type: int
    param40: int
    param41: int
    param49: int
    x_low: int
    depth_raw: int
    column_index: int | None = None
    delay: int | None = None
    x_world: int | None = None

    @property
    def type_id(self) -> int:
        return self.type & 0x7F

    @property
    def two_player_only(self) -> bool:
        return bool(self.type & 0x80)

    @property
    def difficulty(self) -> int:
        return self.depth_raw & 0x03

    @property
    def depth(self) -> int:
        return self.depth_raw & 0xFC

    @property
    def side(self) -> str | None:
        """Spawn edge for camera-relative records (timed/deferred)."""
        if self.kind == "batch":
            return None
        return "right_edge" if self.depth_raw == 0 else "left_edge"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["type_id"] = self.type_id
        data["two_player_only"] = self.two_player_only
        data["difficulty"] = self.difficulty
        data["depth"] = self.depth
        data["side"] = self.side
        return data


def parse_stream(
    data: bytes,
    base_x: int = 0x0300,
    column_stride: int = 0x0100,
    max_blocks: int | None = None,
) -> tuple[list[Record], list[dict], int]:
    """Parse whole blocks.  Returns (records, block summaries, tail offset).

    The round-1 stream ends with a 24-byte tail that does not follow the block
    framing; callers pass max_blocks=4 and record the tail as unknown.
    """
    records: list[Record] = []
    blocks: list[dict] = []
    pos = 0
    block = 0

    def u16(p: int) -> int:
        return (data[p] << 8) | data[p + 1]

    while pos + 1 < len(data):
        if max_blocks is not None and block >= max_blocks:
            break
        block += 1
        start_block = pos
        summary = {"block": block, "start": pos, "batch_counts": [], "timed": 0, "deferred": 0}

        for column in range(3):
            if pos + 1 >= len(data):
                raise ValueError(f"block {block}: truncated batch header at {pos:#x}")
            count = u16(pos)
            pos += 2
            summary["batch_counts"].append(-1 if count & 0x8000 else count + 1)
            if count & 0x8000:
                continue
            for _ in range(count + 1):
                if pos + 6 > len(data):
                    raise ValueError(f"block {block}: truncated batch record at {pos:#x}")
                rec = data[pos:pos + 6]
                index = 3 * (block - 1) + column
                records.append(Record(
                    kind="batch", block=block, column=column, column_index=index,
                    offset=pos,
                    type=rec[0], param40=rec[1], param41=rec[2], param49=rec[3],
                    x_low=rec[4], depth_raw=rec[5],
                    x_world=(base_x + index * column_stride) | rec[4],
                ))
                pos += 6

        # timed list
        while True:
            if pos + 2 > len(data):
                raise ValueError(f"block {block}: timed list ran past the stream")
            delay = u16(pos)
            pos += 2
            if delay == 0x0099:
                break
            if pos + 6 > len(data):
                raise ValueError(f"block {block}: truncated timed record at {pos:#x}")
            summary["timed"] += 1
            rec = data[pos:pos + 6]
            records.append(Record(
                kind="timed", block=block, column=None, offset=pos,
                type=rec[0], param40=rec[1], param41=rec[2], param49=rec[3],
                x_low=rec[4], depth_raw=rec[5], delay=delay & 0x7FFF,
            ))
            pos += 6

        # length-prefixed deferred section
        if pos + 2 > len(data):
            raise ValueError(f"block {block}: missing deferred length")
        length = u16(pos)
        pos += 2
        end = pos + length
        if end > len(data):
            raise ValueError(f"block {block}: deferred section {length:#x} past the stream")
        cursor = pos
        while cursor < end and data[cursor] != 0x99:
            if cursor + 6 > end:
                raise ValueError(f"block {block}: truncated deferred record at {cursor:#x}")
            summary["deferred"] += 1
            rec = data[cursor:cursor + 6]
            records.append(Record(
                kind="deferred", block=block, column=None, offset=cursor,
                type=rec[0], param40=rec[1], param41=rec[2], param49=rec[3],
                x_low=rec[4], depth_raw=rec[5],
            ))
            cursor += 6
        pos = end
        summary["end"] = pos
        blocks.append(summary)
        if pos == start_block:
            break
        if pos >= len(data):
            break
    return records, blocks, pos


def census(records: list[Record]) -> dict:
    out: dict[int, dict] = {}
    for rec in records:
        block = out.setdefault(rec.block, {"batch": 0, "timed": 0, "deferred": 0, "types": {}})
        block[rec.kind] += 1
        block["types"][rec.type_id] = block["types"].get(rec.type_id, 0) + 1
    return out
