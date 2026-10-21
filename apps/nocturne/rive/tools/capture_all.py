#!/usr/bin/env python3
"""Regenerates the review captures under ../captures/ (headless, no window).

python3 tools/capture_all.py

The full motion walkthrough is ../../video.webm (scripts/render-video.py nocturne);
this script only writes stills: settled scenes, personas, key transition frames
(the GPU iris, the lit moon, the meteor fan, the loupe), reduced motion,
fixtures, interaction states and the three presentation sizes.
"""
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CAP = os.path.join(ROOT, "captures")
RIVE = os.path.expanduser("~/.rive/bin/rive")
NEXT = "--pointer=click@195,780"
PREV = "--pointer=click@70,780"
AWAY = "--pointer=move@380,20"
JOBS = 3


def taps(btn, n, gap=26):
    out = []
    for _ in range(n):
        out += [btn, f"--advance={gap}", AWAY, "--advance=2"]
    return out


def keys(n, dwell=150):
    """Reach scene n+1 with the Right key, the way the walkthrough video does."""
    out = []
    for _ in range(n):
        out += [f"--advance={dwell}", "--key=right"]
    return out


def fixture(name):
    data = json.load(open(os.path.join(ROOT, "fixtures", name + ".json")))
    out = []
    for k, v in data.items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        if k == "personaColor":
            v = str(v).lstrip("#")
        out.append(f"--data={k}={v}")
    return out


JOBS_LIST = []


def shot(rel, *flags):
    JOBS_LIST.append((rel, list(flags)))


def run(job):
    rel, flags = job
    path = os.path.join(CAP, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = subprocess.run([RIVE, ".", f"--screenshot={path}", "--quiet", "--data=autoAdvanceEnabled=false"] + flags,
                       cwd=ROOT, capture_output=True, text=True)
    return ("ok  " if r.returncode == 0 else "ERR ") + rel + ("" if r.returncode == 0 else "\n" + r.stderr[-600:])


def stills():
    for k in range(1, 11):
        shot(f"settled/scene-{k:02d}.png", *keys(k - 1), "--advance=240")
    for i in range(4):
        shot(f"personas/persona-{i}.png", f"--data=personaIndex={i}", *keys(8), "--advance=240")
    shot("personas/persona-3-mid-reveal.png", "--data=personaIndex=3", *keys(8), "--advance=96")
    # the signature transition: the stage iris closes over scene 2, travels, opens on scene 3
    for f in (8, 15, 21, 30, 40):
        shot(f"transitions/iris-forward-02-to-03-f{f:02d}.png", *keys(1), "--advance=150", "--key=right", f"--advance={f}")
    for f in (2, 20, 40):
        shot(f"transitions/app-opening-f{f:02d}.png", f"--advance={f}")
    for f in (10, 20):
        shot(f"transitions/iris-back-04-to-03-f{f:02d}.png", *keys(3), "--advance=150", "--key=left", f"--advance={f}")
    for f in (25, 43):
        shot(f"transitions/persona-anticipation-f{f:02d}.png", *keys(8), f"--advance={f}")
    for f in (40, 70):
        shot(f"transitions/moon-phase-sweep-f{f:02d}.png", *keys(5), "--advance=150", "--key=right", f"--advance={f}")
    shot("transitions/meteor-fan-f42.png", *keys(4), "--advance=150", "--key=right", "--advance=42")
    shot("transitions/loupe-develops-f110.png", *keys(6), "--advance=150", "--key=right", "--advance=110")
    for f in (40, 90):
        shot(f"transitions/summary-assembly-f{f:02d}.png", *keys(9), f"--advance={f}")
    rm = ["--data=reducedMotion=true"]
    for k in (1, 2, 7, 9, 10):
        shot(f"reduced-motion/scene-{k:02d}.png", *rm, *keys(k - 1), "--advance=30")
    shot("reduced-motion/transition-3-to-4-frame-6.png", *rm, *keys(3), "--advance=6")
    nu = fixture("new-user")
    shot("fixtures/new-user-01-intro.png", *nu, "--advance=240")
    shot("fixtures/new-user-10-summary.png", *nu, "--advance=10", *taps(NEXT, 1), "--advance=240")
    ex = fixture("extreme-long-copy")
    for k in (1, 2, 3, 6, 9, 10):
        shot(f"fixtures/extreme-{k:02d}.png", *ex, "--advance=10", *taps(NEXT, k - 1), "--advance=240")
    shot("interaction/finder-drag.png", "--advance=90", "--pointer=drag@135,242>150,330:16", "--advance=20")
    shot("interaction/paused.png", "--advance=150", "--pointer=click@320,780", "--advance=10", AWAY, "--advance=2")
    shot("interaction/hold-to-pause.png", "--advance=150", "--pointer=down@300,400", "--advance=60")
    shot("interaction/focus-after-tab.png", "--advance=90", "--key=tab", "--advance=10")
    shot("interaction/summary-share-focused.png", *keys(9), "--advance=240")
    # captureMode hides the chrome (and the focused control with it), so reach the summary with taps
    shot("interaction/share-capture-mode.png", "--data=captureMode=true", "--advance=10", *taps(NEXT, 9), "--advance=240")
    shot("interaction/share-with-name.png", "--data=shareIncludeName=true", *keys(9), "--advance=240")
    shot("interaction/hidden-scenes-3-4-9.png", "--data=showScreen3=false", "--data=showScreen4=false", "--data=showScreen9=false",
         "--advance=10", *taps(NEXT, 2), "--advance=240")
    shot("interaction/runtime-update-nights-512.png", "--data=observationNights=512", *keys(1), "--advance=240")
    shot("interaction/grouping-de-DE.png", "--data=locale=de-DE", "--data=objectsLogged=1284567", *keys(2), "--advance=240")
    for vp in ("320x568", "430x932", "1440x900"):
        shot(f"viewports/{vp}-contain-scene-02.png", f"--viewport={vp}", "--fit=contain", *keys(1), "--advance=240")


if __name__ == "__main__":
    stills()
    with ThreadPoolExecutor(JOBS) as ex:
        for line in ex.map(run, JOBS_LIST):
            print(line)
