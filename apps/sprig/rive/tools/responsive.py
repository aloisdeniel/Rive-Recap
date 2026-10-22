#!/usr/bin/env python3
"""Responsive captures: render scenes across the viewport matrix and assemble contact sheets.

    python3 tools/responsive.py                      # every scene, both orientations -> captures/responsive/
    python3 tools/responsive.py --scenes 2,9 --out /tmp/x --jobs 2
    python3 tools/responsive.py --mid                # also mid-transition frames (1->2 forward, 4->3 back)

Scenes are reached with the Right arrow (the keyboard surface is focused at boot), so navigation works
at every size. Each frame is a headless `rive . --screenshot --viewport=WxH` (layout fit: the artboard is
resized to the viewport). Sheets are built with ffmpeg: one row per orientation, each capture scaled to a
common height, in matrix order (portrait: 320x568 360x640 390x844 430x932 600x960 767x1024 667x375 740x360;
landscape: 768x1024 820x1180 1024x768 1280x720 1440x900 1920x1080 2560x1080 1366x600).
"""
import argparse
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIVE = shutil.which("rive") or os.path.expanduser("~/.rive/bin/rive")
FONT = os.path.join(PROJ, "assets", "fonts", "DMSans-Variable.ttf")

PORTRAIT = [(320, 568), (360, 640), (390, 844), (430, 932), (600, 960), (767, 1024), (667, 375), (740, 360)]
LANDSCAPE = [(768, 1024), (820, 1180), (1024, 768), (1280, 720), (1440, 900), (1920, 1080), (2560, 1080), (1366, 600)]


def steps_to(k, settle, back_from=None):
    """Right-arrow presses 40 frames apart; `settle` counts from the LAST press (so a mid-transition
    frame really is that many frames into the transition)."""
    args = ["--advance=30"]
    target = back_from if back_from else k
    for i in range(1, target):
        if i > 1:
            args.append("--advance=40")
        args.append("--key=right")
    if back_from:
        args += ["--advance=200", "--key=left"]
    args.append(f"--advance={settle}")
    return args


def render(out, w, h, args, data=()):
    cmd = [RIVE, PROJ, "--quiet", f"--screenshot={out}", f"--viewport={w}x{h}"] + [f"--data={d}" for d in data] + args
    for _ in range(2):
        if subprocess.run(cmd, capture_output=True).returncode == 0 and os.path.exists(out):
            return True
    return False


def sheet(rows, out, height=300):
    """rows: [[(png, label)]] -> one png, rows stacked, each capture scaled to `height` and labelled."""
    inputs, filters, row_labels = [], [], []
    n = 0
    for r, row in enumerate(rows):
        names = []
        for png, label in row:
            inputs += ["-i", png]
            # (this ffmpeg build has no drawtext: captures keep the matrix order documented in the README)
            filters.append(f"[{n}:v]scale=-2:{height},pad=iw+12:ih+12:6:6:color=0x111111[c{n}]")
            names.append(f"[c{n}]")
            n += 1
        if len(names) > 1:
            filters.append(f"{''.join(names)}hstack=inputs={len(names)}[r{r}]")
        else:
            filters.append(f"{names[0]}null[r{r}]")
        row_labels.append(f"[r{r}]")
    if len(row_labels) > 1:
        # rows can differ in width: pad each to the widest
        filters.append(f"{''.join(row_labels)}xstack=inputs={len(row_labels)}:layout="
                       + "|".join("0_" + ("+".join(f"h{i}" for i in range(r)) or "0") for r in range(len(row_labels)))
                       + ":fill=0x111111[out]")
    else:
        filters.append(f"{row_labels[0]}null[out]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[out]",
                                                             "-frames:v", "1", out]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="1,2,3,4,5,6,7,8,9,10")
    ap.add_argument("--out", default=os.path.join(PROJ, "captures", "responsive"))
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--settle", type=int, default=170)
    ap.add_argument("--mid", action="store_true", help="also capture mid-transition frames")
    ap.add_argument("--orient", default="pl", help="p, l or pl")
    ap.add_argument("--data", action="append", default=[])
    ap.add_argument("--keep", action="store_true", help="keep the individual frames")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    frames = os.path.join(a.out, "frames")
    os.makedirs(frames, exist_ok=True)
    scenes = [int(s) for s in a.scenes.split(",") if s]
    sizes = (PORTRAIT if "p" in a.orient else []) + (LANDSCAPE if "l" in a.orient else [])
    jobs = []
    settle = {9: 260, 10: 200}
    for k in scenes:
        for w, h in sizes:
            jobs.append((f"scene{k:02d}", k, w, h, steps_to(k, settle.get(k, a.settle))))
    if a.mid:
        for w, h in sizes:
            jobs.append(("mid-fwd-1to2-f20", 2, w, h, steps_to(2, 20)))
            jobs.append(("mid-back-4to3-f18", 3, w, h, steps_to(3, 18, back_from=4)))

    def run(j):
        tag, k, w, h, args = j
        out = os.path.join(frames, f"{tag}-{w}x{h}.png")
        ok = render(out, w, h, args, a.data)
        return tag, w, h, out, ok

    results = {}
    with ThreadPoolExecutor(a.jobs) as ex:
        for tag, w, h, out, ok in ex.map(run, jobs):
            if not ok:
                print("FAILED", tag, w, h)
                continue
            results.setdefault(tag, []).append(((w, h), out))
    for tag, items in sorted(results.items()):
        lookup = dict(items)
        rows = []
        for group in ((PORTRAIT, "portrait"), (LANDSCAPE, "landscape")):
            row = [(lookup[s], f"{s[0]}x{s[1]}") for s in group[0] if s in lookup]
            if row:
                rows.append(row)
        out = os.path.join(a.out, f"{tag}.png")
        sheet(rows, out)
        print("sheet", out)
    if not a.keep:
        shutil.rmtree(frames, ignore_errors=True)


if __name__ == "__main__":
    main()
