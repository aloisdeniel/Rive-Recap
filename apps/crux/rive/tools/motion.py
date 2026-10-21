#!/usr/bin/env python3
"""Renders a motion preview of the recap (headless frames -> ffmpeg mp4).

    python3 tools/motion.py full        # whole story, auto-advance at the 3 s minimum, 15 fps
    python3 tools/motion.py transitions # forward yank 2->3 and reverse lower-off 5->4 at 30 fps

The CLI has no video export, so every frame is its own deterministic headless
capture (--advance in 60 fps steps), rendered in parallel and stitched by ffmpeg.
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RIVE = os.path.expanduser("~/.rive/bin/rive")
OUT = os.path.join(ROOT, "captures", "motion")


def render(frames_dir, idx, steps, data):
    path = os.path.join(frames_dir, f"f{idx:05d}.png")
    cmd = [RIVE, ROOT, "--quiet", f"--screenshot={path}"] + [f"--data={d}" for d in data] + steps
    subprocess.run(cmd, capture_output=True)


def make(name, fps, seconds, data, prefix=(), workers=4):
    frames_dir = os.path.join(OUT, name + "-frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir)
    step = 60 // fps
    n = int(seconds * fps)
    jobs = []
    for i in range(n):
        f = 1 + i * step
        jobs.append((i, list(prefix) + [f"--advance={f}"]))
    with ThreadPoolExecutor(workers) as ex:
        for i, steps in jobs:
            ex.submit(render, frames_dir, i, steps, data)
    mp4 = os.path.join(OUT, name + ".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i",
                    os.path.join(frames_dir, "f%05d.png"), "-pix_fmt", "yuv420p", "-vf", "scale=390:844",
                    "-c:v", "libx264", "-crf", "20", mp4])
    shutil.rmtree(frames_dir, ignore_errors=True)
    print("wrote", mp4)


def main():
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1:] or ["full", "transitions"]
    if "full" in which:
        make("story-full-autoadvance", 15, 56, ["autoAdvanceSeconds=3"])
    if "transitions" in which:
        make("transition-forward-2to3", 30, 3.2, ["currentScreen=2"],
             ["--advance=130", "--pointer=click@300,400"])
        make("transition-reverse-5to4", 30, 3.2, ["currentScreen=5"],
             ["--advance=130", "--pointer=click@60,400"])
        make("persona-power-mover", 30, 2.2, ["currentScreen=9", "personaIndex=1"])


if __name__ == "__main__":
    main()
