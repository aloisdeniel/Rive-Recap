#!/usr/bin/env python3
"""Render a motion preview (MP4) of a full auto-advanced run, frame by frame.

Each frame is an independent headless capture at time t (the runtime is
deterministic at 60 fps), so timing in the video is the real timing.
    python3 tools/motion_preview.py [fps] [seconds] [dwell]
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

RIVE = os.environ.get("RIVE", os.path.expanduser("~/.rive/bin/rive"))
fps = int(sys.argv[1]) if len(sys.argv) > 1 else 15
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 52
dwell = sys.argv[3] if len(sys.argv) > 3 else "3"
SP = os.environ.get("FRAMES_DIR", "build/preview_frames")
os.makedirs(SP, exist_ok=True)
step = 60 // fps
frames = list(range(1, int(secs * 60), step))


def shot(i_f):
    i, f = i_f
    out = f"{SP}/f{i:05d}.png"
    if not os.path.exists(out):
        subprocess.run([RIVE, ".", "--quiet", f"--screenshot={out}", f"--data=autoAdvanceSeconds={dwell}",
                        f"--advance={f}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(shot, enumerate(frames)))
os.makedirs("captures/motion", exist_ok=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps), "-i", f"{SP}/f%05d.png",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "captures/motion/autoplay-full-run.mp4"], check=True)
print("wrote captures/motion/autoplay-full-run.mp4", len(frames), "frames")
