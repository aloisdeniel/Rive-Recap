#!/usr/bin/env python3
"""Render a recap walkthrough video for one app.

    scripts/render-video.py <appname> [--fps 30] [--dwell 3.5] [--tail 3] [--jobs N]

The Rive CLI has no video export, so every frame is its own headless
`rive <project> --screenshot` run that replays the same input script up to that
frame's time: wait `dwell` seconds on a scene, press Right, repeat until the
summary, then hold for `tail` seconds. Frames render in parallel and are
encoded with ffmpeg (mp4, used by merge-videos.py) and img2webp (animated webp,
since Homebrew's ffmpeg has no libwebp encoder).

Outputs:
    apps/<app>/video.webp              animated webp, loops forever
    apps/<app>/rive/build/video.mp4    near-lossless intermediate for merging
"""
import argparse
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIVE = shutil.which("rive") or os.path.expanduser("~/.rive/bin/rive")
TICKS = 60  # the CLI steps animation at 60 fps


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("app", help="directory name under apps/, e.g. simmer")
    p.add_argument("--fps", type=int, default=30, help="output frame rate; must divide 60 (default 30)")
    p.add_argument("--dwell", type=float, default=3.5, help="seconds on each scene before pressing Right (default 3.5)")
    p.add_argument("--tail", type=float, default=3.0, help="seconds to hold the final summary (default 3)")
    p.add_argument("--scenes", type=int, default=10, help="number of scenes to walk through (default 10)")
    p.add_argument("--viewport", default="390x844", help="capture size (default 390x844)")
    p.add_argument("--quality", type=int, default=75, help="webp quality 0-100 (default 75)")
    p.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2), help="parallel renders")
    p.add_argument("--data", action="append", default=[], help="extra view model values, path=value (repeatable)")
    p.add_argument("--keep-frames", action="store_true", help="keep the PNG frames in rive/build/video-frames")
    a = p.parse_args()
    if TICKS % a.fps:
        p.error(f"--fps must divide {TICKS}")
    return a


def frame_args(tick, key_ticks):
    """Input script that ends exactly `tick` animation frames in."""
    args, now = [], 0
    for k in key_ticks:
        if k >= tick:
            break
        if k > now:
            args.append(f"--advance={k - now}")
        args.append("--key=right")
        now = k
    args.append(f"--advance={max(1, tick - now)}")
    return args


def render(project, path, steps, data, viewport):
    cmd = [RIVE, project, "--quiet", f"--screenshot={path}", f"--viewport={viewport}"]
    cmd += [f"--data={d}" for d in data] + steps
    for _ in range(2):  # one retry for a transient failure
        if subprocess.run(cmd, capture_output=True).returncode == 0 and os.path.exists(path):
            return True
    return False


def main():
    a = parse_args()
    project = os.path.join(ROOT, "apps", a.app, "rive")
    if not os.path.isfile(os.path.join(project, "rive.yaml")):
        sys.exit(f"no Rive project at {project}")
    for tool in ("ffmpeg", "img2webp"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH (brew install ffmpeg webp)")

    dwell, step = round(a.dwell * TICKS), TICKS // a.fps
    key_ticks = [dwell * j for j in range(1, a.scenes)]
    total = key_ticks[-1] + round(a.tail * TICKS) if key_ticks else round(a.tail * TICKS)
    ticks = list(range(1, total + 1, step))
    # Hold the auto-advance timer off so only our key presses move the story.
    data = ["autoAdvanceEnabled=false"] + a.data

    frames = os.path.join(project, "build", "video-frames")
    shutil.rmtree(frames, ignore_errors=True)
    os.makedirs(frames)
    print(f"{a.app}: rendering {len(ticks)} frames ({total / TICKS:.1f}s at {a.fps} fps, {a.jobs} jobs)")

    def job(i):
        path = os.path.join(frames, f"f{i:05d}.png")
        return render(project, path, frame_args(ticks[i], key_ticks), data, a.viewport)

    done = 0
    with ThreadPoolExecutor(a.jobs) as ex:
        for ok in ex.map(job, range(len(ticks))):
            if not ok:
                sys.exit(f"{a.app}: frame {done} failed; run `rive {project} --verify`")
            done += 1
            if done % 100 == 0 or done == len(ticks):
                print(f"  {done}/{len(ticks)}", flush=True)

    mp4 = os.path.join(project, "build", "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", os.path.join(frames, "f%05d.png"), "-c:v", "libx264", "-crf", "12",
                    "-preset", "medium", "-pix_fmt", "yuv420p", mp4], check=True)

    webp = os.path.join(ROOT, "apps", a.app, "video.webp")
    pngs = sorted(os.path.join(frames, f) for f in os.listdir(frames) if f.endswith(".png"))
    subprocess.run(["img2webp", "-loop", "0", "-lossy", "-q", str(a.quality), "-m", "4",
                    "-d", str(round(1000 / a.fps)), *pngs, "-o", webp],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not a.keep_frames:
        shutil.rmtree(frames, ignore_errors=True)
    print(f"{a.app}: wrote {os.path.relpath(webp, ROOT)} ({os.path.getsize(webp) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
