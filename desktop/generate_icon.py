"""Generate a simple PNG app icon for electron-builder."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "icon.png"


def _chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def write_icon(path: Path, size: int = 512) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for y in range(size):
        row = b"\x00"
        for x in range(size):
            cx = (x - size / 2) / (size / 2)
            cy = (y - size / 2) / (size / 2)
            in_circle = cx * cx + cy * cy <= 0.72
            if in_circle:
                row += bytes((37, 99, 235, 255))
            else:
                row += bytes((15, 23, 42, 255))
        rows.append(row)
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(raw, 9))
    png += _chunk(b"IEND", b"")
    path.write_bytes(png)


if __name__ == "__main__":
    write_icon(OUT)
    print(f"Wrote {OUT}")
