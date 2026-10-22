#!/usr/bin/env python3
"""Headless capture suite for the Crux recap.

    python3 tools/capture.py [job-prefix ...]     # from apps/crux/rive

Writes PNGs to captures/ (and data dumps to captures/data/). Fixtures are applied
with --data so the same .riv is exercised with every dataset.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RIVE = os.path.expanduser("~/.rive/bin/rive")
OUT = os.path.join(ROOT, "captures")
SKIP = {"currentScreen", "screenProgress"}


def fixture_args(name):
    if not name:
        return []
    with open(os.path.join(ROOT, "fixtures", name + ".json")) as f:
        data = json.load(f)
    args = []
    for k, v in data.items():
        if k in SKIP:
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, str) and v.startswith("#") and len(v) == 7:
            v = "FF" + v[1:]
        args.append(f"--data={k}={v}")
    return args


def run(name, steps, fixture=None, data=(), viewport=None, dump=False, fit=None):
    os.makedirs(OUT, exist_ok=True)
    cmd = [RIVE, ROOT, "--quiet"]
    if dump:
        os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
        cmd.append(f"--data-dump={os.path.join(OUT, 'data', name + '.json')}")
    else:
        cmd.append(f"--screenshot={os.path.join(OUT, name + '.png')}")
    if viewport:
        cmd.append(f"--viewport={viewport}")
    if fit:
        cmd.append(f"--fit={fit}")
    cmd += fixture_args(fixture)
    cmd += [f"--data={d}" for d in data]
    cmd += steps
    r = subprocess.run(cmd, capture_output=True, text=True)
    err = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l.lower()]
    print(("FAIL " if r.returncode else "ok   ") + name, *err[:3])


SETTLE = ["--advance=130"]
NEXT = ["--pointer=click@300,400"]
BACK = ["--pointer=click@60,400"]


def jobs():
    j = []
    for n in range(1, 11):
        j.append((f"scene-{n:02d}-settled", SETTLE, None, [f"currentScreen={n}"]))
    for p in range(4):
        j.append((f"persona-{p}", SETTLE, None, ["currentScreen=9", f"personaIndex={p}"]))
    # transitions: intermediate frames (forward yank, reverse lower-off, continuity carry)
    for a, frames in ((2, (6, 20, 30, 46)), (6, (20, 30, 46)), (8, (20, 30, 46)), (4, (20, 30))):
        for f in frames:
            j.append((f"transition-{a}to{a + 1}-f{f:02d}", SETTLE + NEXT + [f"--advance={f}"], None, [f"currentScreen={a}"]))
    for f in (8, 22, 34, 50):
        j.append((f"transition-back-5to4-f{f:02d}", SETTLE + BACK + [f"--advance={f}"], None, ["currentScreen=5"]))
    # reduced motion
    for n in (2, 6, 9, 10):
        j.append((f"reduced-motion-scene-{n:02d}", ["--advance=20"], None, [f"currentScreen={n}", "reducedMotion=true"]))
    j.append(("reduced-motion-transition-3to4-f06", ["--advance=40"] + NEXT + ["--advance=6"], None, ["currentScreen=3", "reducedMotion=true"]))
    # fixtures
    j.append(("fixture-newuser-intro", SETTLE, "new-user", ["currentScreen=1"]))
    j.append(("fixture-newuser-summary", SETTLE + NEXT + ["--advance=150"], "new-user", ["currentScreen=1"]))
    for n in (1, 2, 4, 6, 7, 8, 9, 10):
        j.append((f"fixture-extreme-scene-{n:02d}", SETTLE, "extreme", [f"currentScreen={n}"]))
    # summary privacy
    j.append(("summary-share-name-on", SETTLE, None, ["currentScreen=10", "shareIncludeName=true"]))
    # responsive validation: the full portrait / landscape matrix is tools/responsive.py
    # (captures/responsive/); these are the 390 x 844 design-size stills
    # interaction: drag the hold (compress), release (rebound)
    j.append(("interaction-hold-drag", ["--advance=120", "--pointer=down@115,605", "--pointer=move@150,560",
                                        "--pointer=move@200,520", "--advance=4"], None, ["currentScreen=1"]))
    j.append(("interaction-hold-released", ["--advance=120", "--pointer=drag@115,605>220,500:8", "--advance=40"], None, ["currentScreen=1"]))
    j.append(("interaction-hold-to-pause", ["--advance=130", "--pointer=down@300,400", "--advance=40"], None, ["currentScreen=3"]))
    j.append(("interaction-paused", ["--advance=130", "--pointer=click@108,783", "--advance=60"], None, ["currentScreen=3"]))
    return j


def main():
    pref = sys.argv[1:]
    for job in jobs():
        name = job[0]
        if pref and not any(name.startswith(p) for p in pref):
            continue
        run(name, job[1], job[2], job[3], job[4] if len(job) > 4 else None, fit=job[5] if len(job) > 5 else None)


if __name__ == "__main__":
    main()
