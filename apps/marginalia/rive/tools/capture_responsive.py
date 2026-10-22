#!/usr/bin/env python3
"""Responsive validation matrix -> captures/responsive/ contact sheets.

    python3 tools/capture_responsive.py            # all scenes, all sizes
    python3 tools/capture_responsive.py 1 9 10     # some scenes

Every scene is captured settled (3200 ms after arrival) at the 16 sizes of
the validation matrix (8 portrait, 8 landscape), plus a mid-turn frame
(scene 4 -> 5 at 330 ms) per size, and tiled into one JPEG sheet per scene:
the portrait row on top, the landscape row below, each labelled WxH.
Tiling needs Pillow (pip install pillow); without it the individual PNGs
are kept in captures/responsive/frames/.
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "captures", "responsive")
FRAMES = os.path.join(OUT, "frames")
PORTRAIT = ["320x568", "360x640", "390x844", "430x932", "600x960", "767x1024", "667x375", "740x360"]
LANDSCAPE = ["768x1024", "820x1180", "1024x768", "1280x720", "1440x900", "1920x1080", "2560x1080", "1366x600"]
JOBS = int(os.environ.get("JOBS", "3"))


def shot(scene, ms, vp, path):
    if not os.path.exists(path):
        subprocess.run([sys.executable, os.path.join(HERE, "capture.py"), "one", str(scene), str(ms), path,
                        f"--viewport={vp}"], check=False)
    return path


def sheet(paths, out, title):
    from PIL import Image, ImageDraw
    rows, H = [], 280
    for group in (PORTRAIT, LANDSCAPE):
        row = []
        for vp in group:
            im = Image.open(paths[vp]).convert("RGB")
            row.append((vp, im.resize((max(1, round(im.width * H / im.height)), H), Image.LANCZOS)))
        rows.append(row)
    W = max(sum(im.width + 10 for _, im in r) + 10 for r in rows)
    canvas = Image.new("RGB", (W, len(rows) * (H + 30) + 40), (54, 52, 50))
    d = ImageDraw.Draw(canvas)
    d.text((10, 10), title, fill=(255, 255, 255))
    y = 34
    for r in rows:
        x = 10
        for vp, im in r:
            canvas.paste(im, (x, y + 16))
            d.text((x, y + 2), vp, fill=(230, 220, 200))
            x += im.width + 10
        y += H + 30
    canvas.save(out, quality=88, optimize=True)


def main():
    scenes = [int(a) for a in sys.argv[1:]] or list(range(1, 11))
    os.makedirs(FRAMES, exist_ok=True)
    jobs = []
    for s in scenes:
        for vp in PORTRAIT + LANDSCAPE:
            jobs.append((s, 3200, vp, os.path.join(FRAMES, f"scene-{s:02d}-{vp}.png")))
    for vp in PORTRAIT + LANDSCAPE:
        jobs.append((5, 330, vp, os.path.join(FRAMES, f"turn-04-05-{vp}.png")))
    with ThreadPoolExecutor(JOBS) as ex:
        list(ex.map(lambda j: shot(*j), jobs))
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow not found: frames kept in", FRAMES)
        return
    for s in scenes:
        paths = {vp: os.path.join(FRAMES, f"scene-{s:02d}-{vp}.png") for vp in PORTRAIT + LANDSCAPE}
        sheet(paths, os.path.join(OUT, f"scene-{s:02d}.jpg"),
              f"Scene {s}, settled - portrait (< 768 wide) above, landscape (>= 768) below")
    paths = {vp: os.path.join(FRAMES, f"turn-04-05-{vp}.png") for vp in PORTRAIT + LANDSCAPE}
    sheet(paths, os.path.join(OUT, "turn-04-to-05-330ms.jpg"), "Page turn 4 -> 5, 330 ms in (mid-transition)")
    shutil.rmtree(FRAMES, ignore_errors=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
