#!/usr/bin/env python3
"""Lay PNG captures side by side into one contact sheet (ffmpeg only, no PIL).

    contact_sheet.py OUT.png --height 420 --row-width 2400 IMG [IMG ...]

Each image is scaled to the same height (keeping its aspect), given a small
oat gutter, and packed left to right into rows no wider than --row-width.
Rows are padded to the widest row and stacked.
"""
import argparse
import os
import subprocess
import sys

GAP = 12
BG = "0xE8DCC8"


def size_of(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", path], capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split("x")
    return int(w), int(h)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out")
    p.add_argument("images", nargs="+")
    p.add_argument("--height", type=int, default=420)
    p.add_argument("--row-width", type=int, default=2400)
    a = p.parse_args()
    imgs = [i for i in a.images if os.path.exists(i)]
    if not imgs:
        sys.exit("no images")
    widths = []
    for i in imgs:
        w, h = size_of(i)
        widths.append(int(round(w * a.height / h / 2)) * 2)
    rows, cur, cw = [], [], 0
    for idx, w in enumerate(widths):
        if cur and cw + w + GAP > a.row_width:
            rows.append(cur)
            cur, cw = [], 0
        cur.append(idx)
        cw += w + GAP
    rows.append(cur)
    row_w = max(sum(widths[i] + GAP for i in r) + GAP for r in rows)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for i in imgs:
        cmd += ["-i", i]
    f = []
    for idx, w in enumerate(widths):
        f.append(f"[{idx}:v]scale={w}:{a.height},pad={w + GAP}:{a.height + GAP}:{GAP}:{GAP}:color={BG}[c{idx}]")
    for ri, r in enumerate(rows):
        ins = "".join(f"[c{i}]" for i in r)
        w = sum(widths[i] + GAP for i in r)
        if len(r) > 1:
            f.append(f"{ins}hstack=inputs={len(r)}[h{ri}]")
        else:
            f.append(f"{ins}null[h{ri}]")
        f.append(f"[h{ri}]pad={row_w}:{a.height + GAP}:0:0:color={BG}[r{ri}]")
    ins = "".join(f"[r{ri}]" for ri in range(len(rows)))
    if len(rows) > 1:
        f.append(f"{ins}vstack=inputs={len(rows)},pad=iw:ih+{GAP}:0:0:color={BG}[out]")
    else:
        f.append(f"{ins}pad=iw:ih+{GAP}:0:0:color={BG}[out]")
    cmd += ["-filter_complex", ";".join(f), "-map", "[out]", "-frames:v", "1", a.out]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
