#!/usr/bin/env python3
"""Merge the per-app recap videos into one showcase.

    scripts/merge-videos.py [--apps a,b,c,...] [--per-row 5] [--scale 0.6] [--fps 15]

Apps play side by side, `per-row` at a time (5 by default, so ten apps make two
sequences), and the sequences play one after another. The defaults keep the
file small enough to show inline in a README; raise --scale and --fps for a
full-quality cut. Reads the intermediates written by render-video.py
(apps/<app>/rive/build/video.mp4), so render the apps first.

Output: apps/showcase.webp
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The gallery order from apps/README.md.
APPS = ["sprig", "crux", "simmer", "marginalia", "nocturne",
        "kiln", "switchyard", "stash", "parlance", "patchwork"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apps", default=",".join(APPS), help="comma-separated app order")
    p.add_argument("--per-row", type=int, default=5, help="apps playing side by side per sequence (default 5)")
    p.add_argument("--scale", type=float, default=0.6, help="scale each 390x844 app tile (default 0.6)")
    p.add_argument("--gap", type=int, default=16, help="pixels around each tile (default 16)")
    p.add_argument("--background", default="0x141414", help="gutter colour (default 0x141414)")
    p.add_argument("--fps", type=int, default=15, help="output frame rate (default 15)")
    p.add_argument("--quality", type=int, default=70, help="webp quality 0-100 (default 70)")
    p.add_argument("--output", default=os.path.join(ROOT, "apps", "showcase.webp"))
    return p.parse_args()


def main():
    a = parse_args()
    apps = [s.strip() for s in a.apps.split(",") if s.strip()]
    videos = [os.path.join(ROOT, "apps", app, "rive", "build", "video.mp4") for app in apps]
    missing = [app for app, v in zip(apps, videos) if not os.path.exists(v)]
    if missing:
        sys.exit("render these first with scripts/render-video.py: " + ", ".join(missing))
    for tool in ("ffmpeg", "img2webp"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH (brew install ffmpeg webp)")

    g = a.gap
    tile = f"scale=trunc(iw*{a.scale}/2)*2:-2,pad=iw+{2 * g}:ih+{2 * g}:{g}:{g}:color={a.background}"
    rows = [list(range(i, min(i + a.per_row, len(apps)))) for i in range(0, len(apps), a.per_row)]
    graph = [f"[{i}:v]{tile},setpts=PTS-STARTPTS[t{i}]" for i in range(len(apps))]
    for r, row in enumerate(rows):
        # A short last row is padded to full width so every sequence is the same size.
        ins = "".join(f"[t{i}]" for i in row)
        stack = f"{ins}hstack=inputs={len(row)}" if len(row) > 1 else f"{ins}null"
        width = f"pad=iw*{a.per_row}/{len(row)}:ih:(ow-iw)/2:0:color={a.background}"
        graph.append(f"{stack},{width}[s{r}]")
    seqs = "".join(f"[s{r}]" for r in range(len(rows)))
    graph.append(f"{seqs}concat=n={len(rows)}:v=1:a=0,fps={a.fps}[out]" if len(rows) > 1 else f"{seqs}fps={a.fps}[out]")

    with tempfile.TemporaryDirectory() as frames:
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for v in videos:
            cmd += ["-i", v]
        cmd += ["-filter_complex", ";".join(graph), "-map", "[out]", os.path.join(frames, "f%05d.png")]
        print(f"merging {len(apps)} apps into {len(rows)} sequence(s) of {a.per_row}")
        subprocess.run(cmd, check=True)

        pngs = sorted(os.path.join(frames, f) for f in os.listdir(frames))
        print(f"encoding {len(pngs)} frames to webp")
        subprocess.run(["img2webp", "-loop", "0", "-lossy", "-q", str(a.quality), "-m", "4",
                        "-d", str(round(1000 / a.fps)), *pngs, "-o", a.output],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"wrote {os.path.relpath(a.output, ROOT)} ({os.path.getsize(a.output) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
