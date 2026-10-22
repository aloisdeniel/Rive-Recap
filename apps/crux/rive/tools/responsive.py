#!/usr/bin/env python3
"""Responsive validation matrix: renders scenes at every portrait and landscape size
and assembles one contact sheet per job into captures/responsive/.

    python3 tools/responsive.py                 # every job
    python3 tools/responsive.py scene-02 persona # jobs whose name starts with a prefix
    python3 tools/responsive.py --jobs 2

Each sheet has two rows: the portrait layout (width < 768) on top, the landscape
layout (width >= 768) below, in the order of PORTRAIT and LANDSCAPE below (left to
right). Frames are scaled to a common height, so their proportions are true.
"""
import argparse
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RIVE = shutil.which("rive") or os.path.expanduser("~/.rive/bin/rive")
OUT = os.path.join(ROOT, "captures", "responsive")
TMP = os.path.join(ROOT, "build", "responsive-frames")

PORTRAIT = ["320x568", "360x640", "390x844", "430x932", "600x960", "767x1024", "667x375", "740x360"]
LANDSCAPE = ["768x1024", "820x1180", "1024x768", "1280x720", "1440x900", "1920x1080", "2560x1080", "1366x600"]
SETTLE = ["--advance=130"]
ROW_H = 300


def jobs():
    j = []
    for n in range(1, 11):
        j.append((f"scene-{n:02d}", [f"currentScreen={n}"], SETTLE))
    for p in (1, 2, 3):
        j.append((f"persona-{p}", ["currentScreen=9", f"personaIndex={p}"], SETTLE))
    j.append(("summary-name-on", ["currentScreen=10", "shareIncludeName=true"], SETTLE))
    j.append(("newuser-summary", ["currentScreen=10"] + [f"showScreen{i}=false" for i in range(2, 10)], SETTLE))
    # mid-transition frames: the forward yank 2->3 (continuity carry) and 6->7
    j.append(("transition-2to3-f20", ["currentScreen=2"], SETTLE + ["--key=right", "--advance=20"]))
    j.append(("transition-6to7-f46", ["currentScreen=6"], SETTLE + ["--key=right", "--advance=46"]))
    j.append(("transition-back-5to4-f22", ["currentScreen=5"], SETTLE + ["--key=left", "--advance=22"]))
    j.append(("reduced-motion-scene-04", ["currentScreen=4", "reducedMotion=true"], ["--advance=30"]))
    j.append(("extreme-scene-04", ["currentScreen=4"] + extreme(), SETTLE))
    j.append(("extreme-scene-10", ["currentScreen=10", "shareIncludeName=true"] + extreme(), SETTLE))
    return j


def extreme():
    import json
    with open(os.path.join(ROOT, "fixtures", "extreme.json")) as f:
        data = json.load(f)
    out = []
    for k, v in data.items():
        if k in ("currentScreen", "screenProgress"):
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, str) and v.startswith("#") and len(v) == 7:
            v = "FF" + v[1:]
        out.append(f"{k}={v}")
    return out


def render(path, size, data, steps):
    cmd = [RIVE, ROOT, "--quiet", f"--screenshot={path}", f"--viewport={size}"]
    cmd += [f"--data={d}" for d in data] + steps
    for _ in range(2):
        if subprocess.run(cmd, capture_output=True).returncode == 0 and os.path.exists(path):
            return True
    return False


def sheet(name, frames, dest):
    """frames: [[(png, label)] row]"""
    rows = []
    for i, row in enumerate(frames):
        inputs, filt, labels = [], [], []
        for j, (png, label) in enumerate(row):
            inputs += ["-i", png]
            filt.append(f"[{j}]scale=-2:{ROW_H},pad=iw+12:ih+12:6:6:0x9A968E[f{j}]")
            labels.append(f"[f{j}]")
        out = os.path.join(TMP, f"{name}-row{i}.png")
        filt.append("".join(labels) + f"hstack=inputs={len(row)}")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y"] + inputs + ["-filter_complex", ";".join(filt), out],
                       check=True)
        rows.append(out)
    # pad rows to the widest, then stack
    widths = []
    for r in rows:
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width", "-of", "csv=p=0", r],
                           capture_output=True, text=True)
        widths.append(int(p.stdout.strip()))
    w = max(widths)
    inputs, filt = [], []
    for i, r in enumerate(rows):
        inputs += ["-i", r]
        filt.append(f"[{i}]pad={w}:ih:0:0:0xF1EEE7[r{i}]")
    filt.append("".join(f"[r{i}]" for i in range(len(rows))) + f"vstack=inputs={len(rows)}")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y"] + inputs + ["-filter_complex", ";".join(filt), dest],
                   check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix", nargs="*")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--sheets-only", action="store_true", help="reassemble sheets from rendered frames")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    todo = [j for j in jobs() if not a.prefix or any(j[0].startswith(p) for p in a.prefix)]
    work = []
    for name, data, steps in todo:
        for size in PORTRAIT + LANDSCAPE:
            work.append((os.path.join(TMP, f"{name}-{size}.png"), size, data, steps))
    if a.sheets_only:
        results = [os.path.exists(w[0]) for w in work]
    else:
        with ThreadPoolExecutor(a.jobs) as ex:
            results = list(ex.map(lambda w: render(*w), work))
    failed = [w[0] for w, ok in zip(work, results) if not ok]
    for name, _, _ in todo:
        frames = [[(os.path.join(TMP, f"{name}-{s}.png"), s) for s in PORTRAIT],
                  [(os.path.join(TMP, f"{name}-{s}.png"), s) for s in LANDSCAPE]]
        sheet(name, frames, os.path.join(a.out, f"{name}.png"))
        print("wrote", os.path.relpath(os.path.join(a.out, f"{name}.png"), ROOT))
    if failed:
        print("FAILED:", failed)


if __name__ == "__main__":
    main()
