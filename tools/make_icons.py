"""Generate PWA / app icons without third-party dependencies.

Usage:
    python tools/make_icons.py

Writes PNGs into static/icons/. Only the standard library is used, so this
works on a bare Python install.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / 'static' / 'icons'

# Design canvas is 1000 x 1000; every shape below uses those units.
DESIGN = 1000.0

BRAND_DARK = (11, 37, 69)      # --brand-900  #0b2545
BRAND_LIGHT = (30, 58, 138)    #              #1e3a8a
WHITE = (255, 255, 255)
AMBER = (245, 158, 11)         # --accent     #f59e0b

SUPERSAMPLE = 2


def lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))


def rounded_rect(px: float, py: float, x0: float, y0: float,
                 x1: float, y1: float, radius: float) -> bool:
    if px < x0 or px > x1 or py < y0 or py > y1:
        return False
    cx = min(max(px, x0 + radius), x1 - radius)
    cy = min(max(py, y0 + radius), y1 - radius)
    dx = px - cx
    dy = py - cy
    return dx * dx + dy * dy <= radius * radius


def sample(px: float, py: float, scale: float, offset: float,
           mask_radius: float | None) -> tuple[int, int, int, int]:
    """Return RGBA for a point in design space."""
    if mask_radius is not None:
        if not rounded_rect(px, py, 0, 0, DESIGN, DESIGN, mask_radius):
            return (0, 0, 0, 0)

    # Diagonal brand gradient.
    t = min(max((px * 0.35 + py * 0.65) / DESIGN, 0.0), 1.0)
    colour = (
        lerp(BRAND_DARK[0], BRAND_LIGHT[0], t),
        lerp(BRAND_DARK[1], BRAND_LIGHT[1], t),
        lerp(BRAND_DARK[2], BRAND_LIGHT[2], t),
        255,
    )

    # Map into the glyph box (centred, scaled).
    gx = (px - DESIGN / 2) / scale + DESIGN / 2 + offset
    gy = (py - DESIGN / 2) / scale + DESIGN / 2 + offset

    # Briefcase handle (ring).
    handle_outer = rounded_rect(gx, gy, 400, 250, 600, 430, 70)
    handle_inner = rounded_rect(gx, gy, 448, 298, 552, 430, 34)
    if handle_outer and not handle_inner:
        return (WHITE[0], WHITE[1], WHITE[2], 255)

    # Briefcase body.
    if rounded_rect(gx, gy, 190, 380, 810, 770, 70):
        # Clasp sits on top of the body.
        if rounded_rect(gx, gy, 455, 505, 545, 645, 22):
            return (AMBER[0], AMBER[1], AMBER[2], 255)
        return (WHITE[0], WHITE[1], WHITE[2], 255)

    return colour


def render(size: int, scale: float = 1.0, offset: float = 0.0,
           mask_radius: float | None = 220.0) -> list[bytearray]:
    big = size * SUPERSAMPLE
    step = DESIGN / big
    rows: list[bytearray] = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            r = g = b = a = 0
            for sy in range(SUPERSAMPLE):
                for sx in range(SUPERSAMPLE):
                    px = (x * SUPERSAMPLE + sx + 0.5) * step
                    py = (y * SUPERSAMPLE + sy + 0.5) * step
                    sr, sg, sb, sa = sample(px, py, scale, offset, mask_radius)
                    r += sr * sa
                    g += sg * sa
                    b += sb * sa
                    a += sa
            count = SUPERSAMPLE * SUPERSAMPLE
            if a == 0:
                row += bytes((0, 0, 0, 0))
            else:
                row += bytes((
                    min(255, r // a),
                    min(255, g // a),
                    min(255, b // a),
                    min(255, a // count),
                ))
        rows.append(row)
    return rows


def write_png(path: Path, size: int, rows: list[bytearray]) -> None:
    raw = b''.join(b'\x00' + bytes(row) for row in rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack('>I', len(data))
            + tag
            + data
            + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    png = (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', header)
        + chunk(b'IDAT', zlib.compress(raw, 9))
        + chunk(b'IEND', b'')
    )
    path.write_bytes(png)
    print(f'  {path.relative_to(OUT_DIR.parent.parent)}  ({len(png) // 1024} KB)')


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print('Generating app icons...')

    # Standard icons: rounded square, full-size glyph.
    for size in (192, 512):
        write_png(OUT_DIR / f'icon-{size}.png', size, render(size))

    # Maskable icon: full bleed, glyph shrunk into the safe zone.
    write_png(
        OUT_DIR / 'icon-maskable-512.png',
        512,
        render(512, scale=0.78, mask_radius=None),
    )

    # iOS home screen icon: iOS applies its own corner mask.
    write_png(
        OUT_DIR / 'apple-touch-icon.png',
        180,
        render(180, scale=0.92, mask_radius=None),
    )

    # Browser tab icon.
    write_png(
        OUT_DIR / 'favicon-32.png',
        32,
        render(32, scale=1.05, mask_radius=None),
    )

    print('Done.')


if __name__ == '__main__':
    main()
