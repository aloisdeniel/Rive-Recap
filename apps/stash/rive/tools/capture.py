#!/usr/bin/env python3
"""Capture the review set under captures/ (run from the project dir).

Fixtures are applied the way a host adapter would: every JSON field is written
into the one bound UserRecap instance (`--data=name=value`); colour strings
are adapted from "#RRGGBB" to the native colour property.

    python3 tools/capture.py            # everything
    python3 tools/capture.py settled    # one group
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

RIVE = os.environ.get("RIVE", os.path.expanduser("~/.rive/bin/rive"))
CAP = "captures"
RUNTIME = {"currentScreen", "screenProgress"}  # owned by the state machine, never pushed by fixtures


def fixture_flags(name):
    data = json.load(open(f"fixtures/{name}.json"))
    out = []
    for k, v in data.items():
        if k in RUNTIME:
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, str) and v.startswith("#") and len(v) == 7:
            v = "FF" + v[1:]
        out.append(f"--data={k}={v}")
    return out


def shot(path, args):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run([RIVE, ".", "--quiet", f"--screenshot={path}"] + args, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path


def sheet(paths, out, width=1300):
    paths = [p for p in paths if os.path.exists(p)]
    args = []
    for p in paths:
        args += ["-i", p]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y"] + args +
                   ["-filter_complex", f"hstack=inputs={len(paths)},scale={width}:-1", out], check=True)


SEEN = ["--data=_count1=1", "--data=_count2=1"]  # earlier scenes already counted (as in a real run)
JOBS = []


def job(path, args):
    JOBS.append((path, args))


def settled(fx="sample", folder="settled", extra=()):
    flags = fixture_flags(fx) + list(extra)
    for k in range(1, 11):
        job(f"{CAP}/{folder}/scene{k:02d}.png", flags + SEEN + [f"--data=currentScreen={k}", "--advance=2.8s"])


def groups():
    g = {}
    g["settled"] = lambda: settled()
    g["reduced"] = lambda: settled(folder="reduced-motion", extra=["--data=reducedMotion=true"])
    g["zero"] = lambda: [job(f"{CAP}/fixtures/zero-user/scene{k:02d}.png",
                             fixture_flags("zero-user") + [f"--data=currentScreen={k}", "--advance=2.8s"]) for k in (1, 10)]
    g["extreme"] = lambda: settled("extreme-long-copy", "fixtures/extreme-long-copy")

    def personas():
        for i in range(4):
            job(f"{CAP}/personas/persona{i}.png", fixture_flags("sample") + SEEN +
                [f"--data=personaIndex={i}", "--data=currentScreen=9", "--advance=3s"])
            job(f"{CAP}/personas/persona{i}-reveal-midframe.png", fixture_flags("sample") + SEEN +
                [f"--data=personaIndex={i}", "--data=currentScreen=9", "--advance=1.25s"])
    g["personas"] = personas

    def transitions():
        for k in range(1, 10):
            base = fixture_flags("sample") + SEEN + [f"--data=currentScreen={k}", "--advance=2.6s", "--key=right"]
            job(f"{CAP}/transitions/forward-{k:02d}-to-{k + 1:02d}-f26.png", base + ["--advance=26"])
            job(f"{CAP}/transitions/forward-{k:02d}-to-{k + 1:02d}-f34.png", base + ["--advance=34"])
            back = fixture_flags("sample") + SEEN + [f"--data=currentScreen={k + 1}", "--advance=2.6s", "--key=left"]
            job(f"{CAP}/transitions/back-{k + 1:02d}-to-{k:02d}-f24.png", back + ["--advance=24"])
        rm = fixture_flags("sample") + SEEN + ["--data=reducedMotion=true", "--data=currentScreen=2", "--advance=1s", "--key=right"]
        job(f"{CAP}/reduced-motion/transition-02-to-03-f8.png", rm + ["--advance=8"])
        for f in (8, 16, 24, 28, 32, 40):
            job(f"{CAP}/transitions/signature-02-to-03/frame{f:02d}.png",
                fixture_flags("sample") + SEEN + ["--data=currentScreen=2", "--advance=2.6s", "--key=right", f"--advance={f}"])
    g["transitions"] = transitions

    def viewports():
        for vp in ("320x568", "430x932", "1440x900"):
            for k in (1, 2, 9, 10):
                job(f"{CAP}/viewports/{vp}/scene{k:02d}.png", fixture_flags("sample") + SEEN +
                    [f"--viewport={vp}", f"--data=currentScreen={k}", "--advance=2.8s"])
    g["viewports"] = viewports

    def share():
        base = fixture_flags("sample") + SEEN + ["--data=currentScreen=10", "--advance=3s"]
        job(f"{CAP}/share/summary-private-default.png", base)
        job(f"{CAP}/share/summary-name-and-values.png",
            base[:-1] + ["--data=shareIncludeName=true", "--data=shareIncludeSensitiveValues=true", "--advance=3s"])
        job(f"{CAP}/share/sharecard-artboard-private.png", fixture_flags("sample") + ["--artboard=ShareCard", "--advance=10"])
        job(f"{CAP}/share/summary-zero-user.png", fixture_flags("zero-user") + ["--data=currentScreen=10", "--advance=3s"])
    g["share"] = share

    def interaction():
        base = fixture_flags("sample") + SEEN + ["--data=currentScreen=4", "--advance=3s"]
        job(f"{CAP}/interaction/coin-toy-rest.png", base)
        for f in (8, 20, 34):
            job(f"{CAP}/interaction/coin-toy-nudge-f{f}.png", base + ["--pointer=click@129,718", f"--advance={f}"])
        job(f"{CAP}/interaction/keyboard-focus-continue.png", fixture_flags("sample") + ["--advance=1s", "--key=tab", "--key=tab", "--key=tab", "--advance=10"])
        job(f"{CAP}/interaction/paused.png", fixture_flags("sample") + ["--advance=2.5s", "--key=space", "--advance=20"])
        job(f"{CAP}/interaction/runtime-update-before.png", fixture_flags("sample") + SEEN + ["--data=currentScreen=3", "--advance=2.8s"])
        job(f"{CAP}/interaction/runtime-update-after-deposits-4321.png", fixture_flags("sample") + SEEN +
            ["--data=currentScreen=3", "--data=deposits=4321", "--data=locale=de-DE", "--advance=2.8s"])
    g["interaction"] = interaction

    def gpu():
        base = fixture_flags("sample") + SEEN
        job(f"{CAP}/gpu/jar-coins-2x.png", base + ["--viewport=780x1688", "--data=currentScreen=2", "--advance=3s"])
        job(f"{CAP}/gpu/merged-coin-2x.png", base + ["--viewport=780x1688", "--data=currentScreen=5", "--advance=3s"])
        job(f"{CAP}/gpu/arcade-screen-2x.png", base + ["--viewport=780x1688", "--data=currentScreen=6", "--advance=4s"])
        job(f"{CAP}/gpu/goal-tokens-2x.png", base + ["--viewport=780x1688", "--data=currentScreen=4", "--advance=3s"])
        job(f"{CAP}/gpu/springs-fire-2x.png", base + ["--viewport=780x1688", "--data=currentScreen=2", "--advance=3s",
                                                     "--key=right", "--advance=32"])
    g["gpu"] = gpu
    return g


def main():
    gs = groups()
    want = sys.argv[1:] or list(gs)
    for w in want:
        gs[w]()
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda j: shot(*j), JOBS))
    # contact sheets
    for folder in ("settled", "reduced-motion", "fixtures/extreme-long-copy"):
        if os.path.exists(f"{CAP}/{folder}/scene01.png"):
            sheet([f"{CAP}/{folder}/scene{k:02d}.png" for k in range(1, 6)], f"{CAP}/{folder}/sheet-1-5.png")
            sheet([f"{CAP}/{folder}/scene{k:02d}.png" for k in range(6, 11)], f"{CAP}/{folder}/sheet-6-10.png")
    if os.path.exists(f"{CAP}/personas/persona0.png"):
        sheet([f"{CAP}/personas/persona{i}.png" for i in range(4)], f"{CAP}/personas/sheet.png", 1040)
    sig = f"{CAP}/transitions/signature-02-to-03"
    if os.path.exists(f"{sig}/frame04.png"):
        sheet([f"{sig}/frame{f:02d}.png" for f in (8, 16, 24, 28, 32, 40)], f"{sig}/sheet.png", 1560)
    print(f"{len(JOBS)} captures")


if __name__ == "__main__":
    main()
