#!/usr/bin/env python3
"""Renders a complete motion preview (all ten scenes, every page turn) to
captures/motion-preview.mp4 by capturing deterministic headless frames.

    python3 tools/motion_preview.py [fps] [extra rive args...]

Each frame is a separate headless run that replays the same tap script up to
that frame's time, so timing is exact (the capture clock is 1/60 s).
Requires ffmpeg on PATH.
"""
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RIVE = os.path.expanduser("~/.rive/bin/rive")
FPS = int(sys.argv[1]) if len(sys.argv) > 1 else 12
EXTRA = sys.argv[2:]
FIRST, EVERY, TAIL = 2.6, 3.0, 3.0
TAPS = [FIRST + EVERY * k for k in range(9)]
TOTAL = TAPS[-1] + TAIL
NAME = "motion-preview" + ("-" + "-".join(a.split("=")[-2].split("/")[-1] for a in EXTRA if "=" in a) if EXTRA else "")
OUT = os.path.join(ROOT, "build", "frames-" + NAME)


def cmd(i):
    t = i / FPS
    args = [RIVE, ROOT, "--quiet", f"--screenshot={OUT}/f{i:05d}.png", *EXTRA]
    now = 0.0
    for tap in TAPS:
        if tap > t:
            break
        args.append(f"--advance={int(round((tap - now) * 1000))}ms")
        # a click consumes ~2 frames
        args += ["--pointer=click@300,420", "--pointer=move@200,300"]
        now = tap + 3 / 60
    rest = max(1, int(round((t - now) * 1000)))
    args.append(f"--advance={rest}ms")
    return args


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    n = int(TOTAL * FPS)
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda i: subprocess.run(cmd(i), capture_output=True), range(n)))
    dst = os.path.join(ROOT, "captures", f"{NAME}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{OUT}/f%05d.png",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", dst], check=True)
    print("wrote", dst, n, "frames")


if __name__ == "__main__":
    main()
