"""Read data tables out of the IDA-style 68000 listing.

The listing stores raw data as `dc.b` / `dc.w` lines under a label.  This
module extracts those bytes and words together with the line number of every
byte, so a decoded value can always be traced back to the listing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")


@dataclass
class Bytes:
    label: str
    data: bytes
    lines: list[int]  # source line number for each byte

    def hex(self) -> str:
        return self.data.hex(" ")


def read_listing(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _values(payload: str) -> list[int]:
    out = []
    for token in payload.split(","):
        token = token.strip()
        if not token:
            continue
        token = token.replace("$", "0x")
        out.append(int(token, 0))
    return out


def extract_dc_b(lines: list[str], label: str) -> Bytes:
    start = None
    for index, line in enumerate(lines):
        match = LABEL_RE.match(line)
        if match and match.group(1) == label:
            start = index
            break
    if start is None:
        raise KeyError(f"label {label} not found")

    data = bytearray()
    source = []
    for index in range(start, len(lines)):
        line = lines[index]
        match = LABEL_RE.match(line)
        if match and match.group(1) != label and data:
            break
        body = line.split(";", 1)[0]
        if "dc.b" not in body:
            continue
        payload = body.split("dc.b", 1)[1]
        for value in _values(payload):
            data.append(value & 0xFF)
            source.append(index + 1)
    return Bytes(label, bytes(data), source)


def extract_dc_w(lines: list[str], label: str, count: int | None = None) -> list[int]:
    start = None
    for index, line in enumerate(lines):
        match = LABEL_RE.match(line)
        if match and match.group(1) == label:
            start = index
            break
    if start is None:
        raise KeyError(f"label {label} not found")

    values: list[int] = []
    for index in range(start, len(lines)):
        line = lines[index]
        match = LABEL_RE.match(line)
        if match and match.group(1) != label and values:
            break
        body = line.split(";", 1)[0]
        if "dc.w" not in body:
            continue
        payload = body.split("dc.w", 1)[1]
        for value in _values(payload):
            values.append(value & 0xFFFF)
            if count is not None and len(values) >= count:
                return values
    return values
