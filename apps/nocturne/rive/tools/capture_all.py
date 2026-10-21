#!/usr/bin/env python3
"""Regenerates every review capture under ../captures/ (headless, no window).

python3 tools/capture_all.py            # stills
python3 tools/capture_all.py --motion   # also the motion preview (frames + GIF, needs Pillow)
"""
import os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CAP = os.path.join(ROOT, "captures")
RIVE = os.path.expanduser("~/.rive/bin/rive")
NEXT = "--pointer=click@195,780"
PREV = "--pointer=click@70,780"
AWAY = "--pointer=move@380,20"


def taps(btn, n, gap=26):
    out = []
    for _ in range(n):
        out += [btn, f"--advance={gap}", AWAY, "--advance=2"]
    return out


def fixture(name):
    import json
    data = json.load(open(os.path.join(ROOT, "fixtures", name + ".json")))
    out = []
    for k, v in data.items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        if k == "personaColor":
            v = str(v).lstrip("#")
        out.append(f"--data={k}={v}")
    return out


def shot(rel, *flags):
    path = os.path.join(CAP, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    r = subprocess.run([RIVE, ".", f"--screenshot={path}", "--quiet"] + list(flags), cwd=ROOT, capture_output=True, text=True)
    print(("ok  " if r.returncode == 0 else "ERR ") + rel)
    if r.returncode:
        print(r.stderr[-800:])


def stills():
    for k in range(1, 11):
        shot(f"settled/scene-{k:02d}.png", "--advance=10", *taps(NEXT, k - 1), "--advance=200")
    for i in range(4):
        shot(f"personas/persona-{i}.png", f"--data=personaIndex={i}", "--advance=10", *taps(NEXT, 8), "--advance=220")
    rm = ["--data=reducedMotion=true"]
    for k in (1, 4, 7, 9, 10):
        shot(f"reduced-motion/scene-{k:02d}.png", *rm, "--advance=10", *taps(NEXT, k - 1), "--advance=30")
    shot("reduced-motion/transition-3-to-4-frame-6.png", *rm, "--advance=10", *taps(NEXT, 2), NEXT, "--advance=6")
    nu = fixture("new-user")
    shot("fixtures/new-user-01-intro.png", *nu, "--advance=200")
    shot("fixtures/new-user-10-summary.png", *nu, "--advance=10", *taps(NEXT, 1), "--advance=220")
    ex = fixture("extreme-long-copy")
    for k in (1, 2, 3, 6, 9, 10):
        shot(f"fixtures/extreme-{k:02d}.png", *ex, "--advance=10", *taps(NEXT, k - 1), "--advance=220")
    # one intermediate frame (or more) per forward transition, plus reverse transitions
    for k in range(1, 10):
        for f in (8, 20):
            shot(f"transitions/forward-{k:02d}-to-{k + 1:02d}-f{f:02d}.png", "--advance=10", *taps(NEXT, k - 1), "--advance=150",
                 NEXT, f"--advance={f}")
    for k in (3, 7, 10):
        for f in (8, 20):
            shot(f"transitions/back-{k:02d}-to-{k - 1:02d}-f{f:02d}.png", "--advance=10", *taps(NEXT, k - 1), "--advance=150",
                 PREV, f"--advance={f}")
    for f in (20, 50, 90):
        shot(f"transitions/summary-assembly-f{f:03d}.png", "--advance=10", *taps(NEXT, 8), "--advance=150", NEXT, f"--advance={f}")
    shot("transitions/persona-anticipation-f30.png", "--advance=10", *taps(NEXT, 7), "--advance=150", NEXT, "--advance=30")
    # interaction + host states
    shot("interaction/finder-drag.png", "--advance=60", "--pointer=drag@241,262>150,320:16", "--advance=20")
    shot("interaction/paused.png", "--advance=150", "--pointer=click@320,780", "--advance=10", AWAY, "--advance=2")
    shot("interaction/hold-to-pause.png", "--advance=150", "--pointer=down@300,400", "--advance=60")
    shot("interaction/focus-after-tab.png", "--advance=30", "--key=tab", "--advance=10")
    shot("interaction/share-capture-mode.png", "--data=captureMode=true", "--advance=10", *taps(NEXT, 9), "--advance=220")
    shot("interaction/share-with-name.png", "--data=shareIncludeName=true", "--advance=10", *taps(NEXT, 9), "--advance=220")
    shot("interaction/hidden-scenes-3-4-9.png", "--data=showScreen3=false", "--data=showScreen4=false", "--data=showScreen9=false",
         "--advance=10", *taps(NEXT, 2), "--advance=200")
    shot("interaction/runtime-update-nights-512.png", "--data=observationNights=512", "--advance=10", *taps(NEXT, 1), "--advance=200")
    for vp in ("320x568", "430x932", "1440x900"):
        shot(f"viewports/{vp}-contain-scene-02.png", f"--viewport={vp}", "--fit=contain", "--advance=10", *taps(NEXT, 1),
             "--advance=200")


def motion(step=5, dwell=150, total_scenes=10, tail=200):
    frames_dir = os.path.join(CAP, "motion", "frames")
    os.makedirs(frames_dir, exist_ok=True)
    tap_frames = [dwell * (i + 1) for i in range(total_scenes - 1)]
    end = tap_frames[-1] + tail
    names = []
    for t in range(1, end, step):
        flags, cur = [], 0
        for tf in tap_frames:
            if tf < t:
                flags += [f"--advance={tf - cur}", NEXT]
                cur = tf + 2
        flags.append(f"--advance={max(1, t - cur)}")
        name = os.path.join(frames_dir, f"f{t:05d}.png")
        subprocess.run([RIVE, ".", f"--screenshot={name}", "--quiet"] + flags, cwd=ROOT, capture_output=True)
        names.append(name)
    try:
        from PIL import Image
    except ImportError:
        print("Pillow missing: frames written, GIF skipped")
        return
    ims = [Image.open(n).convert("RGB").resize((195, 422)) for n in names]
    ims[0].save(os.path.join(CAP, "motion", "walkthrough.gif"), save_all=True, append_images=ims[1:],
                duration=int(1000 * step / 60), loop=0, optimize=True)
    print("wrote motion/walkthrough.gif", len(ims), "frames")


if __name__ == "__main__":
    if "--motion-only" not in sys.argv:
        stills()
    if "--motion" in sys.argv or "--motion-only" in sys.argv:
        motion()
