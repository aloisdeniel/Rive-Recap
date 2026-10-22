#!/usr/bin/env python3
"""Regenerates the review captures under captures/.

  python3 tools/capture.py            # stills at 390 x 844 (settled, personas, RM, fixtures, transitions, GPU)
  python3 tools/responsive.py         # the responsive viewport matrix (captures/responsive/)
  python3 tools/capture.py --motion   # also an auto-advance GIF (slow; ../video.webm is the walkthrough)

Needs Pillow only for the contact sheets / GIF (falls back to stills if missing).
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import PROJECT, adv, click, rive, shot  # noqa: E402

C = os.path.join(PROJECT, "captures")
NEXT, PREV = (259, 790), (50, 790)


def out(*p):
    path = os.path.join(C, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def sheet(paths, dest, scale=0.6):
    try:
        from PIL import Image
    except ImportError:
        return
    ims = [Image.open(p) for p in paths]
    w, h = int(ims[0].width * scale), int(ims[0].height * scale)
    c = Image.new("RGB", (w * len(ims), h), (245, 242, 233))
    for i, im in enumerate(ims):
        c.paste(im.resize((w, h)), (i * w, 0))
    c.save(dest)


def stills():
    settled = []
    for n in range(1, 11):
        p = out("settled", f"scene{n:02d}.png")
        shot(p, *adv(240), data=[f"currentScreen={n}"])
        settled.append(p)
    sheet(settled[:5], out("settled", "_sheet_1-5.png"))
    sheet(settled[5:], out("settled", "_sheet_6-10.png"))

    personas = []
    for i in range(4):
        p = out("personas", f"persona{i}.png")
        shot(p, *adv(240), data=["currentScreen=9", f"personaIndex={i}"])
        personas.append(p)
        for f in (40, 70, 100):
            shot(out("personas", f"persona{i}_reveal_f{f:03d}.png"), *adv(f),
                 data=["currentScreen=9", f"personaIndex={i}"])
    sheet(personas, out("personas", "_sheet.png"))

    rm = []
    for n in (1, 2, 5, 9, 10):
        p = out("reduced-motion", f"scene{n:02d}_settled.png")
        shot(p, *adv(60), data=[f"currentScreen={n}", "reducedMotion=true"])
        rm.append(p)
    shot(out("reduced-motion", "fade_2to3_f06.png"), *adv(60), *click(*NEXT), *adv(6),
         data=["currentScreen=2", "reducedMotion=true"])
    sheet(rm, out("reduced-motion", "_sheet.png"))

    fx = []
    for n in (1, 10):
        p = out("fixtures", f"zero_scene{n:02d}.png")
        shot(p, *adv(240), fixture="zero-new-user.json", data=[f"currentScreen={n}"])
        fx.append(p)
    shot(out("fixtures", "zero_progress_two_segments.png"), *adv(60), fixture="zero-new-user.json")
    for n in range(1, 11):
        p = out("fixtures", f"extreme_scene{n:02d}.png")
        shot(p, *adv(240), fixture="extreme-long-copy.json", data=[f"currentScreen={n}"])
        fx.append(p)
    shot(out("fixtures", "share_name_opt_in.png"), *adv(240), data=["currentScreen=10", "shareIncludeName=true"])
    shot(out("fixtures", "runtime_update_journeys_9999.png"), *adv(240), data=["currentScreen=2", "journeys=9999"])
    shot(out("fixtures", "locale_de_grouping.png"), *adv(240), data=["currentScreen=3", "locale=de-DE"])
    sheet(fx[2:7], out("fixtures", "_sheet_extreme_1-5.png"))
    sheet(fx[7:12], out("fixtures", "_sheet_extreme_6-10.png"))

    # transitions: forward handoff (two intermediate frames each) + reverse collapse
    for n in range(1, 10):
        frames = []
        for f in (14, 26, 40):
            p = out("transitions", f"fwd_{n:02d}to{n + 1:02d}_f{f:02d}.png")
            shot(p, *adv(150), *click(*NEXT), *adv(f), data=[f"currentScreen={n}"])
            frames.append(p)
        sheet(frames, out("transitions", f"_fwd_{n:02d}to{n + 1:02d}.png"), 0.5)
    for n in (3, 6, 10):
        frames = []
        for f in (10, 22, 34):
            p = out("transitions", f"back_{n:02d}to{n - 1:02d}_f{f:02d}.png")
            shot(p, *adv(150), *click(*PREV), *adv(f), data=[f"currentScreen={n}"])
            frames.append(p)
        sheet(frames, out("transitions", f"_back_{n:02d}to{n - 1:02d}.png"), 0.5)
    for f in (20, 60, 110):
        shot(out("transitions", f"route_chip_B12_f{f:03d}.png"), *adv(150), *click(146, 488), *adv(f),
             data=["currentScreen=4"])

    # GPU pieces mid-move: the intro camera dive, the tram braking, the flap board rolling
    for f in (40, 60, 80):
        shot(out("gpu", f"intro_world_dive_f{f:03d}.png"), *adv(f), data=["currentScreen=1"])
    for f in (40, 60, 80):
        shot(out("gpu", f"tram_arrival_f{f:03d}.png"), *adv(f), data=["currentScreen=2"])
    for f in (50, 70, 90):
        shot(out("gpu", f"flapboard_roll_f{f:03d}.png"), *adv(f), data=["currentScreen=8"])
    # true pause: two frames 2.5 s apart while paused are identical (idle loops frozen mid-motion)
    shot(out("gpu", "pause_freeze_a.png"), *adv(300), "--key=space", *adv(1), data=["currentScreen=6",
                                                                                 "autoAdvanceEnabled=false"])
    shot(out("gpu", "pause_freeze_b.png"), *adv(300), "--key=space", *adv(150), data=["currentScreen=6",
                                                                                   "autoAdvanceEnabled=false"])

    # responsive layout across the viewport matrix: tools/responsive.py -> captures/responsive/


def motion(step=5, seconds=62):
    try:
        from PIL import Image
    except ImportError:
        print("Pillow missing: skipping GIF")
        return
    tmp = out("motion", "_frames", "x")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    frames = []
    total = seconds * 60
    for f in range(1, total, step):
        p = out("motion", "_frames", f"f{f:05d}.png")
        if not os.path.exists(p):
            shot(p, *adv(f), data=["autoAdvanceSeconds=4"])
        frames.append(Image.open(p).resize((260, 563)).convert("P", palette=Image.ADAPTIVE, colors=96))
    frames[0].save(out("motion", "switchyard-auto-advance.gif"), save_all=True, append_images=frames[1:],
                   duration=int(1000 * step / 60), loop=0, optimize=True)
    shutil.rmtree(os.path.dirname(tmp))


if __name__ == "__main__":
    stills()
    if "--motion" in sys.argv:
        motion()
    print("captures written to", C)
