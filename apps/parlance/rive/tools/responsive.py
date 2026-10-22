#!/usr/bin/env python3
"""Responsive matrix: render scenes across the portrait and landscape viewport matrix and assemble one contact
sheet per scene (sizes side by side, each labelled), plus mid-transition sheets.

usage: python3 tools/responsive.py [--jobs 3] [--scenes 1,2,9] [--sizes 390x844,1280x720] [--out DIR] [--keep]

The CLI's default --fit=layout resizes the artboard to the viewport, exactly like a host using the runtime's
layout fit, so each capture is the real layout at that size. Navigation uses the Right arrow (the file focuses
Continue on boot), which works at every size. Sheets need Pillow (taken from /usr/bin/python3).
"""
import argparse
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIVE = shutil.which("rive") or os.path.expanduser("~/.rive/bin/rive")
PORTRAIT = ["320x568", "360x640", "390x844", "430x932", "600x960", "767x1024", "667x375", "740x360"]
LANDSCAPE = ["768x1024", "820x1180", "1024x768", "1280x720", "1440x900", "1920x1080", "2560x1080", "1366x600"]
# (name, from scene, frames after pressing Right) -- one mid-transition frame per handoff family
TRANSITIONS = [("signature-3to4", 3, 30), ("handoff-5to6", 5, 18), ("persona-8to9", 8, 70), ("summary-9to10", 9, 60),
               ("carry-1to2", 1, 20)]


def nav(n):
    a = ["--advance=150"]
    for _ in range(n - 1):
        a += ["--key=right", "--advance=190"]
    return a


def render(job):
    path, vp, args = job
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [RIVE, ROOT, "--quiet", f"--screenshot={path}", f"--viewport={vp}"] + args
    for _ in range(2):
        if subprocess.run(cmd, capture_output=True).returncode == 0 and os.path.exists(path):
            return True
    return False


SHEET = r'''
import sys
from PIL import Image, ImageDraw, ImageFont
out, title, files = sys.argv[1], sys.argv[2], sys.argv[3:]
H = 300                      # every capture scaled to this height; portrait row then landscape row
ims = []
for f in files:
    im = Image.open(f).convert("RGB")
    w, h = im.size
    ims.append((im.resize((max(1, round(w * H / h)), H), Image.LANCZOS), f.split("/")[-1].rsplit(".", 1)[0].split("@")[-1]))
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    tfont = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20)
except Exception:
    font = tfont = ImageFont.load_default()
rows, row, wsum = [], [], 0
MAXW = 2400
for im, lab in ims:
    if row and wsum + im.size[0] + 12 > MAXW:
        rows.append(row); row, wsum = [], 0
    row.append((im, lab)); wsum += im.size[0] + 12
if row:
    rows.append(row)
W = max(sum(i.size[0] + 12 for i, _ in r) for r in rows) + 12
sheet = Image.new("RGB", (W, 44 + len(rows) * (H + 30)), (34, 30, 40))
d = ImageDraw.Draw(sheet)
d.text((12, 10), title, fill=(255, 248, 236), font=tfont)
y = 44
for r in rows:
    x = 12
    for im, lab in r:
        d.text((x, y + 2), lab, fill=(220, 210, 240), font=font)
        sheet.paste(im, (x, y + 22))
        x += im.size[0] + 12
    y += H + 30
sheet.save(out)
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--scenes", default="1,2,3,4,5,6,7,8,9,10")
    ap.add_argument("--sizes", default=",".join(PORTRAIT + LANDSCAPE))
    ap.add_argument("--out", default=os.path.join(ROOT, "captures", "responsive"))
    ap.add_argument("--no-transitions", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the individual frames in <out>/frames")
    ap.add_argument("--data", action="append", default=[])
    a = ap.parse_args()
    scenes = [int(x) for x in a.scenes.split(",") if x]
    sizes = [x for x in a.sizes.split(",") if x]
    frames_dir = os.path.join(a.out, "frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    data = [f"--data={d}" for d in a.data]
    jobs, sheets = [], []
    for n in scenes:
        files = []
        for vp in sizes:
            p = os.path.join(frames_dir, f"scene-{n:02d}@{vp}.png")
            jobs.append((p, vp, data + nav(n)))
            files.append(p)
        sheets.append((os.path.join(a.out, f"scene-{n:02d}.png"), f"Scene {n} (settled) - portrait sizes, then landscape", files))
    if not a.no_transitions:
        for name, n, f in TRANSITIONS:
            files = []
            for vp in sizes:
                p = os.path.join(frames_dir, f"{name}@{vp}.png")
                jobs.append((p, vp, data + nav(n) + ["--key=right", f"--advance={f}"]))
                files.append(p)
            sheets.append((os.path.join(a.out, f"transition-{name}.png"), f"Mid-transition {name}, {f} frames after Right", files))
    with ThreadPoolExecutor(a.jobs) as ex:
        ok = list(ex.map(render, jobs))
    print(f"{sum(ok)}/{len(ok)} renders")
    for out, title, files in sheets:
        subprocess.run(["/usr/bin/python3", "-c", SHEET, out, title] + [f for f in files if os.path.exists(f)], check=True)
        print("sheet", os.path.relpath(out, ROOT))
    if not a.keep:
        shutil.rmtree(frames_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
