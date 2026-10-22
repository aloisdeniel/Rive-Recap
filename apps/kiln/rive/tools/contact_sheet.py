#!/usr/bin/env python3
"""Tile PNG captures into one labelled contact sheet.

    python3 tools/contact_sheet.py out.png --height 360 --cols 8 a.png b.png ...

Every image is scaled to the same height (aspect kept), laid out left to right in
rows of --cols, and labelled with its file name (minus .png) underneath. Uses
Pillow when it is installed; otherwise ffmpeg, without labels.
"""
from __future__ import annotations

import argparse
import os
import struct
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(os.path.dirname(HERE), "assets", "fonts", "Manrope-VariableFont_wght.ttf")
BG = (29, 27, 26)
INK = (232, 226, 216)


def png_size(path: str) -> tuple[int, int]:
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def layout(images, H, cols, G, LB):
    cells = []
    for p in images:
        w, h = png_size(p)
        cells.append((p, max(2, round(w * H / h))))
    rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    sheet_w = max(sum(w for _, w in r) + G * (len(r) + 1) for r in rows)
    sheet_h = len(rows) * (H + LB + G) + G
    placed, y = [], G
    for r in rows:
        x = G
        for p, w in r:
            placed.append((p, w, x, y))
            x += w + G
        y += H + LB + G
    return sheet_w, sheet_h, placed


def with_pillow(out, images, H, cols, G, LB):
    from PIL import Image, ImageDraw, ImageFont
    sw, sh, placed = layout(images, H, cols, G, LB)
    sheet = Image.new("RGB", (sw, sh), BG)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(FONT, int(LB * 0.6))
    except OSError:
        font = ImageFont.load_default()
    for p, w, x, y in placed:
        im = Image.open(p).convert("RGB").resize((w, H), Image.LANCZOS)
        sheet.paste(im, (x, y))
        if LB:
            label = os.path.splitext(os.path.basename(p))[0]
            tw = draw.textlength(label, font=font)
            draw.text((x + (w - tw) / 2, y + H + LB * 0.15), label, fill=INK, font=font)
    sheet.save(out, optimize=True)


def with_ffmpeg(out, images, H, cols, G):
    sw, sh, placed = layout(images, H, cols, G, 0)
    inputs, filters = [], [f"color=c=0x1d1b1a:s={sw}x{sh}:d=1[bg0]"]
    for i, (p, w, x, y) in enumerate(placed):
        inputs += ["-i", p]
        filters.append(f"[{i}:v]scale={w}:{H}:flags=lanczos[c{i}]")
    prev = "bg0"
    for i, (p, w, x, y) in enumerate(placed):
        filters.append(f"[{prev}][c{i}]overlay={x}:{y}[bg{i + 1}]")
        prev = f"bg{i + 1}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs +
                   ["-filter_complex", ";".join(filters), "-map", f"[{prev}]", "-frames:v", "1", out], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--height", type=int, default=360)
    ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--gap", type=int, default=16)
    ap.add_argument("--label", type=int, default=30, help="label strip height (0 = no labels)")
    a = ap.parse_args()
    try:
        import PIL  # noqa: F401
        with_pillow(a.out, a.images, a.height, a.cols, a.gap, a.label)
    except ImportError:
        with_ffmpeg(a.out, a.images, a.height, a.cols, a.gap)


if __name__ == "__main__":
    main()
