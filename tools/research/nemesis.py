"""Nemesis decompressor (Sega Mega Drive), written from the format description.

The algorithm is the standard one: a 16-bit header carries the tile count and
an XOR flag, a prefix-code table maps 8-bit prefixes to 4-bit pixels with a
run length, and the payload is a big-endian bit stream.  Output is exactly
tile_count * 32 bytes.

Reference for cross-checking (not copied): RuiNelson/StreetsOfRageRecompilation
SoRDecompress.cpp (MIT) and the routine $81A4 (nemesisdec_ram) in the JUE REV 00
listing.  This implementation is independent and is validated against the tile
counts stored in the game's own offset table.
"""
from __future__ import annotations


class NemesisError(ValueError):
    pass


class BitReader:
    def __init__(self, data: bytes, pos: int, buffer: int = 0, bits: int = 0):
        self.data = data
        self.pos = pos
        self.buf = buffer & ((1 << bits) - 1) if bits else 0
        self.nbits = bits

    def _fill(self, need: int) -> None:
        while self.nbits < need:
            if self.pos >= len(self.data):
                # Pad with zeros; the encoder always has enough bytes, but a
                # truncated stream must not crash the parser.
                self.buf = (self.buf << 8) & 0xFFFFFFFFFFFF
                self.nbits += 8
                continue
            self.buf = ((self.buf << 8) | self.data[self.pos]) & 0xFFFFFFFFFFFF
            self.pos += 1
            self.nbits += 8

    def peek(self, count: int) -> int:
        self._fill(count)
        return (self.buf >> (self.nbits - count)) & ((1 << count) - 1)

    def read(self, count: int) -> int:
        value = self.peek(count)
        self.nbits -= count
        self.buf &= (1 << self.nbits) - 1 if self.nbits else 0
        return value


def decompress(data: bytes) -> bytes:
    if len(data) < 4:
        raise NemesisError("stream too short")
    header = (data[0] << 8) | data[1]
    xor_mode = bool(header & 0x8000)
    tile_count = header & 0x7FFF
    pos = 2

    # prefix table: 256 entries -> (length, token) or None
    table: list[tuple[int, int] | None] = [None] * 256
    group = data[pos]
    pos += 1
    while group != 0xFF:
        pixel = group & 0x0F
        while True:
            if pos >= len(data):
                raise NemesisError("truncated prefix table")
            desc = data[pos]
            pos += 1
            if desc >= 0x80:
                group = desc
                break
            length = desc & 0x0F
            if length == 0 or length > 8:
                raise NemesisError(f"invalid prefix length {length}")
            token = (desc & 0x70) | pixel
            code = data[pos]
            pos += 1
            if code >= (1 << length):
                raise NemesisError(f"prefix code {code} does not fit {length} bits")
            start = code << (8 - length)
            count = 1 << (8 - length)
            for index in range(start, start + count):
                if table[index] is not None:
                    raise NemesisError("overlapping prefix code")
                table[index] = (length, token)

    initial = (data[pos] << 8) | data[pos + 1]
    pos += 2
    bits = BitReader(data, pos, initial, 16)

    out = bytearray()
    rows = tile_count * 8
    previous = 0
    row = 0
    nibbles = 0
    while rows:
        prefix = bits.peek(8)
        if prefix >= 0xFC:
            bits.read(6)
            token = bits.read(7)
        else:
            entry = table[prefix]
            if entry is None:
                raise NemesisError(f"undefined prefix {prefix:02x}")
            length, token = entry
            bits.read(length)
        value = token & 0x0F
        for _ in range((token >> 4) + 1):
            row = ((row << 4) | value) & 0xFFFFFFFF
            nibbles += 1
            if nibbles != 8:
                continue
            if xor_mode:
                row ^= previous
                previous = row
            out += row.to_bytes(4, "big")
            rows -= 1
            row = 0
            nibbles = 0
            if rows == 0:
                break
    return bytes(out)
