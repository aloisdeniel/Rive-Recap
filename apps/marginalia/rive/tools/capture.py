#!/usr/bin/env python3
"""Headless capture helper: drives the recap with synthetic taps and saves PNGs.

    python3 tools/capture.py settled            # captures/settled/scene-01..10.png
    python3 tools/capture.py one 4 2000 out.png # scene 4, 2000 ms after arrival
    python3 tools/capture.py one 4 300 out.png --data reducedMotion=true

Taps go to the right two-thirds of the stage (artboard coords 300,420), which
is the "next" zone. Between taps a short advance lets each page turn start.
"""
import os
import json
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RIVE = os.path.expanduser("~/.rive/bin/rive")


def fixture_args(name):
    with open(os.path.join(ROOT, "fixtures", f"{name}.json")) as f:
        data = json.load(f)
    out = []
    for k, v in data.items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, str) and v.startswith("#"):
            v = v[1:]
        out.append(f"--data={k}={v}")
    return out


def run(scene, ms, out, extra=(), viewport=None, gap="900ms", fit=None):
    args = [RIVE, ROOT, f"--screenshot={out}", "--quiet"]
    for e in extra:
        args.append(e)
    if viewport:
        args.append(f"--viewport={viewport}")
    if fit:
        args.append(f"--fit={fit}")
    args.append("--advance=300ms")
    for i in range(scene - 1):
        args += ["--pointer=click@300,420", "--pointer=move@200,420"]
        if i < scene - 2:
            args.append(f"--advance={gap}")
    args.append(f"--advance={ms}ms")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
    return out


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "settled":
        d = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "captures", "settled")
        extra = []
        for x in sys.argv[3:]:
            extra += fixture_args(x[10:]) if x.startswith("--fixture=") else [f"--data={x}"]
        for s in range(1, 11):
            run(s, 3200, os.path.join(d, f"scene-{s:02d}.png"), extra)
            print("scene", s)
    elif mode == "one":
        s, ms, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        extra = []
        vp = None
        fit = None
        for x in sys.argv[5:]:
            if x.startswith("--viewport="):
                vp = x.split("=", 1)[1]
            elif x.startswith("--fit="):
                fit = x.split("=", 1)[1]
            elif x.startswith("--fixture="):
                extra += fixture_args(x.split("=", 1)[1])
            else:
                extra.append(x if x.startswith("--") else f"--data={x}")
        run(s, ms, out, extra, vp, fit=fit)
