#!/usr/bin/env python3
"""Render a recap walkthrough video for one app.

    scripts/render-video.py <appname> [--fps 30] [--dwell 3.5] [--tail 3] [--jobs N]

The Rive CLI has no video export, so every frame is its own headless
`rive <project> --screenshot` run that replays the same input script up to that
frame's time: wait `dwell` seconds on a scene, press Right, repeat until the
summary, then hold for `tail` seconds. Frames render in parallel and are
encoded directly to VP9 WebM with ffmpeg. merge-videos.py reads these same
files; no intermediate video or animated-image encoder is needed.

Outputs:
    apps/<app>/video.webm              VP9 video (looping is controlled by the player)
    --output path                      write elsewhere, e.g. a landscape render:
        scripts/render-video.py <app> --viewport 1280x720 --output apps/<app>/video-landscape.webm
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
    p.add_argument("--quality", type=int, default=75, help="VP9 quality 0-100, higher is better; maps to CRF 63-0 (default 75)")
    p.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2), help="parallel renders")
    p.add_argument("--data", action="append", default=[], help="extra view model values, path=value (repeatable)")
    p.add_argument("--keep-frames", action="store_true", help="keep the PNG frames in rive/build/video-frames-<name>")
    p.add_argument("--output", help="output .webm (default apps/<app>/video.webm), e.g. apps/<app>/video-landscape.webm")
    a = p.parse_args()
    if a.fps <= 0 or TICKS % a.fps:
        p.error(f"--fps must divide {TICKS}")
    if not 0 <= a.quality <= 100:
        p.error("--quality must be between 0 and 100")
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
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH (install ffmpeg with the libvpx-vp9 encoder)")

    dwell, step = round(a.dwell * TICKS), TICKS // a.fps
    key_ticks = [dwell * j for j in range(1, a.scenes)]
    total = key_ticks[-1] + round(a.tail * TICKS) if key_ticks else round(a.tail * TICKS)
    ticks = list(range(1, total + 1, step))
    # Hold the auto-advance timer off so only our key presses move the story.
    data = ["autoAdvanceEnabled=false"] + a.data

    webm = os.path.abspath(a.output) if a.output else os.path.join(ROOT, "apps", a.app, "video.webm")
    if not webm.endswith(".webm"):
        sys.exit("--output must end in .webm")
    # Per-output frame directory, so a portrait and a landscape render can run at once.
    frames = os.path.join(project, "build", "video-frames-" + os.path.splitext(os.path.basename(webm))[0])
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

    crf = round(63 * (1 - a.quality / 100))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", os.path.join(frames, "f%05d.png"),
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                    "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(crf),
                    "-deadline", "good", "-cpu-used", "2", "-row-mt", "1",
                    "-pix_fmt", "yuv420p", "-an", "-f", "webm", webm], check=True)

    if not a.keep_frames:
        shutil.rmtree(frames, ignore_errors=True)
    print(f"{a.app}: wrote {os.path.relpath(webm, ROOT)} ({os.path.getsize(webm) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
