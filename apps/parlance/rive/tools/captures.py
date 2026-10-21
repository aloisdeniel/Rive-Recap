#!/usr/bin/env python3
"""Regenerate every capture in captures/ (settled scenes, personas, fixtures, reduced motion, transition frames,
viewports, the concept side-by-side and motion-preview.gif). Stale files are removed first so nothing piles up.

usage: python3 tools/captures.py            (from apps/parlance/rive; Pillow is taken from /usr/bin/python3)
"""
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "captures")
RIVE = os.path.expanduser("~/.rive/bin/rive")
NEXT, BACK = "--pointer=click@260,790", "--pointer=click@50,790"


def nav(n):
    a = ["--advance=150"]
    for _ in range(n - 1):
        a += [NEXT, "--advance=190"]
    return a


def fixture_flags(path):
    import json
    import math
    fx = json.load(open(os.path.join(ROOT, path)))
    out = []
    for k, v in fx.items():
        if k in ("currentScreen", "screenProgress", "personaName", "personaDescription", "personaColor"):
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in ("year", "personaIndex", "autoAdvanceSeconds"):
            v = int(round(v)) if math.isfinite(v) and v > 0 else 0
        if isinstance(v, bool):
            v = "true" if v else "false"
        out.append(f"--data={k}={v}")
    return out


JOBS = []


def shot(rel, args):
    JOBS.append((os.path.join(CAP, rel), args))


# settled scenes
for n in range(1, 11):
    shot(f"settled/scene-{n:02d}.png", nav(n))
# personas (scene 9) and their summary cards
for k in range(4):
    shot(f"personas/persona-{k}.png", [f"--data=personaIndex={k}"] + nav(9))
    shot(f"personas/summary-persona-{k}.png", [f"--data=personaIndex={k}"] + nav(10))
shot("personas/summary-name-and-minutes-shared.png",
     ["--data=shareIncludeName=true", "--data=shareIncludeSensitiveValues=true"] + nav(10))
# reduced motion
for n in (1, 3, 9, 10):
    shot(f"reduced-motion/scene-{n:02d}.png", ["--data=reducedMotion=true"] + nav(n))
shot("reduced-motion/fade-2-to-3-frame6.png", ["--data=reducedMotion=true"] + nav(2) + [NEXT, "--advance=6"])
# fixtures
ext, zero = fixture_flags("fixtures/extreme.json"), fixture_flags("fixtures/zero-user.json")
for n in (1, 2, 3, 4, 5, 9, 10):
    shot(f"fixtures/extreme-scene-{n:02d}.png", ext + nav(n))
shot("fixtures/zero-user-intro.png", zero + ["--advance=150"])
shot("fixtures/zero-user-summary.png", zero + ["--advance=150", NEXT, "--advance=250"])
shot("fixtures/hidden-3-and-4-progress.png", ["--data=showScreen3=false", "--data=showScreen4=false"] + nav(3))
# transition frames: (name, from scene, direction, frames after the tap)
TRANS = [("carry-1to2", 1, NEXT, [12, 24, 40]), ("carry-2to3", 2, NEXT, [12, 24, 40]),
         ("signature-3to4", 3, NEXT, [6, 16, 28, 40, 48, 54, 64, 76]),
         ("handoff-4to5", 4, NEXT, [8, 18, 26, 36, 46]), ("handoff-6to7", 6, NEXT, [18, 34, 44]),
         ("handoff-7to8", 7, NEXT, [18, 34, 44]), ("persona-8to9", 8, NEXT, [44, 70, 98, 120, 160]),
         ("summary-9to10", 9, NEXT, [44, 76, 104, 140]),
         ("reverse-5to4", 5, BACK, [8, 16, 24, 36, 50]), ("reverse-3to2", 3, BACK, [14, 26, 44])]
for name, n, d, frames in TRANS:
    for f in frames:
        shot(f"transitions/{name}-f{f:03d}.png", nav(n) + [d, f"--advance={f}"])


def run(job):
    path, args = job
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = subprocess.run([RIVE, ROOT, "--quiet", f"--screenshot={path}"] + args, capture_output=True)
    return r.returncode == 0


if __name__ == "__main__":
    for sub in ("settled", "personas", "reduced-motion", "fixtures", "transitions", "viewports"):
        shutil.rmtree(os.path.join(CAP, sub), ignore_errors=True)
    for stale in ("motion-preview.gif", "concept-vs-build.png"):
        if os.path.exists(os.path.join(CAP, stale)):
            os.remove(os.path.join(CAP, stale))
    for vp in ("320x568", "430x932", "1280x800"):
        JOBS.append((os.path.join(CAP, "viewports", f"{vp}-contain.png"), [f"--viewport={vp}", "--fit=contain"] + nav(2)))
    with ThreadPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 4) as ex:
        ok = list(ex.map(run, JOBS))
    print(f"{sum(ok)}/{len(ok)} captures")
    # concept side-by-side (needs Pillow)
    subprocess.run(["/usr/bin/python3", os.path.join(ROOT, "tools", "concept_compare.py")], check=False)
    # motion preview from the walkthrough video
    video = os.path.join(os.path.dirname(ROOT), "video.webm")
    if os.path.exists(video):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-vf",
                        "fps=8,scale=180:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none",
                        os.path.join(CAP, "motion-preview.gif")], check=False)
