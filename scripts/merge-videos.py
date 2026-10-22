#!/usr/bin/env python3
"""Merge the per-app recap videos into one showcase.

    scripts/merge-videos.py [--apps a,b,c,...] [--per-row 5] [--rows 2] [--scale 0.6] [--fps 15]
    scripts/merge-videos.py --video video-landscape.webm --rows 2 --scale 0.35 \
        --output apps/showcase-landscape.webm     # all ten landscape renders at once

Apps play in a grid of `per-row` columns by `rows` rows (5 x 2 by default, so
all ten apps play at once). More apps than fit in one grid make further
sequences that play one after another; `--rows 1` gives single rows of five. The defaults keep the
file small enough for a web preview; raise --scale and --fps for a
full-quality cut. Reads the WebM videos written by render-video.py
(apps/<app>/video.webm, or the file named by --video), so render the apps first.

Output: apps/showcase.webm (VP9; looping is controlled by the player)
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The gallery order from apps/README.md.
APPS = ["sprig", "crux", "simmer", "marginalia", "nocturne",
        "kiln", "switchyard", "stash", "parlance", "patchwork"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apps", default=",".join(APPS), help="comma-separated app order")
    p.add_argument("--per-row", type=int, default=5, help="apps playing side by side per row (default 5)")
    p.add_argument("--rows", type=int, default=2, help="rows stacked in each sequence (default 2)")
    p.add_argument("--video", default="video.webm", help="per-app video file name (default video.webm)")
    p.add_argument("--scale", type=float, default=0.6, help="scale each 390x844 app tile (default 0.6)")
    p.add_argument("--gap", type=int, default=16, help="pixels around each tile (default 16)")
    p.add_argument("--background", default="0x141414", help="gutter colour (default 0x141414)")
    p.add_argument("--fps", type=int, default=15, help="output frame rate (default 15)")
    p.add_argument("--quality", type=int, default=70, help="VP9 quality 0-100, higher is better; maps to CRF 63-0 (default 70)")
    p.add_argument("--output", default=os.path.join(ROOT, "apps", "showcase.webm"))
    a = p.parse_args()
    if not 0 <= a.quality <= 100:
        p.error("--quality must be between 0 and 100")
    if not a.output.lower().endswith(".webm"):
        p.error("--output must end in .webm")
    if a.rows < 1 or a.per_row < 1 or a.fps < 1 or a.scale <= 0 or a.gap < 0:
        p.error("--per-row, --fps and --scale must be positive; --gap must be nonnegative")
    return a


def main():
    a = parse_args()
    apps = [s.strip() for s in a.apps.split(",") if s.strip()]
    if not apps:
        sys.exit("--apps must contain at least one app")
    videos = [os.path.join(ROOT, "apps", app, a.video) for app in apps]
    missing = [app for app, v in zip(apps, videos) if not os.path.exists(v)]
    if missing:
        sys.exit("render these first with scripts/render-video.py: " + ", ".join(missing))
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH (install ffmpeg with the libvpx-vp9 encoder)")

    g = a.gap
    tile = f"scale=trunc(iw*{a.scale}/2)*2:-2,pad=iw+{2 * g}:ih+{2 * g}:{g}:{g}:color={a.background}"
    per_seq = a.per_row * a.rows
    seqs_idx = [list(range(i, min(i + per_seq, len(apps)))) for i in range(0, len(apps), per_seq)]
    graph = [f"[{i}:v]{tile},setpts=PTS-STARTPTS[t{i}]" for i in range(len(apps))]
    for q, seq in enumerate(seqs_idx):
        row_labels = []
        for r in range(a.rows):
            row = seq[r * a.per_row:(r + 1) * a.per_row]
            if not row:
                break
            # A short row is padded to full width so every row and sequence is the same size.
            ins = "".join(f"[t{i}]" for i in row)
            stack = f"{ins}hstack=inputs={len(row)}" if len(row) > 1 else f"{ins}null"
            width = f"pad=iw*{a.per_row}/{len(row)}:ih:(ow-iw)/2:0:color={a.background}"
            graph.append(f"{stack},{width}[r{q}_{r}]")
            row_labels.append(f"[r{q}_{r}]")
        # Pad missing rows so every sequence has the same height.
        height = f"pad=iw:ih*{a.rows}/{len(row_labels)}:0:0:color={a.background}"
        vs = f"{''.join(row_labels)}vstack=inputs={len(row_labels)}" if len(row_labels) > 1 else f"{row_labels[0]}null"
        graph.append(f"{vs},{height}[s{q}]")
    seqs = "".join(f"[s{q}]" for q in range(len(seqs_idx)))
    graph.append(f"{seqs}concat=n={len(seqs_idx)}:v=1:a=0,fps={a.fps}[out]" if len(seqs_idx) > 1 else f"{seqs}fps={a.fps}[out]")

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for v in videos:
        cmd += ["-i", v]
    crf = round(63 * (1 - a.quality / 100))
    cmd += ["-filter_complex", ";".join(graph), "-map", "[out]",
            "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(crf),
            "-deadline", "good", "-cpu-used", "2", "-row-mt", "1",
            "-pix_fmt", "yuv420p", "-an", "-f", "webm", a.output]
    print(f"merging {len(apps)} apps into {len(seqs_idx)} sequence(s) of {a.rows}x{a.per_row}")
    subprocess.run(cmd, check=True)
    print(f"wrote {os.path.relpath(a.output, ROOT)} ({os.path.getsize(a.output) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
