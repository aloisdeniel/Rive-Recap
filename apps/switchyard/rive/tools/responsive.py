#!/usr/bin/env python3
"""Responsive matrix captures for the Switchyard recap.

Renders scenes at the portrait and landscape viewport matrix with the CLI's
default `--fit=layout` (the artboard is resized to the viewport, as a host's
layout fit does) and writes one contact sheet per scene to
captures/responsive/ (top row portrait sizes, bottom row landscape sizes).

  python3 tools/responsive.py                    # settled scenes 1-10 + transitions
  python3 tools/responsive.py --scenes 2 9 --sizes 390x844 1280x720 --out /tmp/x
  python3 tools/responsive.py --keep             # keep the individual PNGs

Contact sheets need Pillow (`/usr/bin/python3` on macOS ships it).
"""
import argparse
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import PROJECT, RIVE  # noqa: E402

PORTRAIT = ["320x568", "360x640", "390x844", "430x932", "600x960", "767x1024", "667x375", "740x360"]
LANDSCAPE = ["768x1024", "820x1180", "1024x768", "1280x720", "1440x900", "1920x1080", "2560x1080", "1366x600"]


def render(path, vp, data, steps):
    cmd = [RIVE, ".", "--quiet", f"--screenshot={path}", f"--viewport={vp}"] + [f"--data={d}" for d in data] + steps
    for _ in range(2):
        p = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True)
        if p.returncode == 0 and os.path.exists(path):
            return True
    print("FAILED", path, p.stdout[-400:], p.stderr[-400:])
    return False


def sheet(rows, dest, title):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow missing: no contact sheet for", dest)
        return
    th = {0: 300, 1: 230}
    pad, lab = 14, 22
    tiles = []
    for r, row in enumerate(rows):
        line = []
        for vp, p in row:
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGB")
            h = th[r]
            w = max(1, round(im.width * h / im.height))
            line.append((vp, im.resize((w, h), Image.LANCZOS)))
        tiles.append(line)
    width = max(sum(t[1].width + pad for t in line) + pad for line in tiles if line)
    height = 40 + sum(th[r] + lab + pad for r in range(len(tiles)))
    c = Image.new("RGB", (width, height), (40, 44, 50))
    d = ImageDraw.Draw(c)
    d.text((pad, 12), title, fill=(245, 242, 233))
    y = 40
    for r, line in enumerate(tiles):
        x = pad
        for vp, im in line:
            d.text((x, y), vp, fill=(255, 214, 75) if r == 0 else (120, 170, 255))
            c.paste(im, (x, y + lab))
            x += im.width + pad
        y += th[r] + lab + pad
    c.save(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", type=int, nargs="*", default=list(range(1, 11)))
    ap.add_argument("--sizes", nargs="*", default=None)
    ap.add_argument("--out", default=os.path.join(PROJECT, "captures", "responsive"))
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--no-transitions", action="store_true")
    ap.add_argument("--data", action="append", default=[])
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    sizes = a.sizes or (PORTRAIT + LANDSCAPE)
    raw = os.path.join(a.out, "_frames")
    os.makedirs(raw, exist_ok=True)

    jobs = []
    for n in a.scenes:
        for vp in sizes:
            jobs.append((f"s{n:02d}{a.tag}_{vp}.png", vp, [f"currentScreen={n}"] + a.data, ["--advance=260"]))
    if not a.no_transitions:
        # one mid-transition frame per orientation: the roundel breathing out 4 -> 5
        # and the persona reveal, plus the reverse collapse 3 -> 2
        for vp in sizes:
            jobs.append((f"t45{a.tag}_{vp}.png", vp, ["currentScreen=4"] + a.data,
                         ["--advance=150", "--key=right", "--advance=34"]))
            jobs.append((f"t32{a.tag}_{vp}.png", vp, ["currentScreen=3"] + a.data,
                         ["--advance=150", "--key=left", "--advance=12"]))
    with ThreadPoolExecutor(a.jobs) as ex:
        list(ex.map(lambda j: render(os.path.join(raw, j[0]), j[1], j[2], j[3]), jobs))

    def rows(prefix):
        return [[(vp, os.path.join(raw, f"{prefix}{a.tag}_{vp}.png")) for vp in sizes if vp in PORTRAIT],
                [(vp, os.path.join(raw, f"{prefix}{a.tag}_{vp}.png")) for vp in sizes if vp not in PORTRAIT]]

    names = {1: "invitation", 2: "journeys", 3: "km", 4: "routes", 5: "stations", 6: "ferry", 7: "weekend",
             8: "months", 9: "persona", 10: "summary"}
    for n in a.scenes:
        sheet(rows(f"s{n:02d}"), os.path.join(a.out, f"scene{n:02d}_{names[n]}{a.tag}.png"),
              f"Scene {n} ({names[n]}) settled - top: portrait layout (< 768 wide), bottom: landscape layout")
    if not a.no_transitions:
        sheet(rows("t45"), os.path.join(a.out, f"transition_4to5_roundel{a.tag}.png"),
              "Forward handoff 4 -> 5, frame 34: the roundel breathing out to cover the whole artboard")
        sheet(rows("t32"), os.path.join(a.out, f"transition_3to2_reverse{a.tag}.png"),
              "Reverse 3 -> 2, frame 12: the scene collapsing back into its roundel")
    if not a.keep:
        shutil.rmtree(raw, ignore_errors=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
