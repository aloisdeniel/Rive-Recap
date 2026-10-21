"""Small wrapper around the headless `rive` CLI used by capture.py / scenario tests."""
import json
import os
import subprocess

RIVE = os.path.expanduser("~/.rive/bin/rive")
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fixture_args(name):
    """--data flags for a fixture JSON (colors converted to ARGB)."""
    if not name:
        return []
    d = json.load(open(os.path.join(PROJECT, "fixtures", name)))
    out = []
    for k, v in d.items():
        if k in ("currentScreen", "screenProgress"):
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, str) and v.startswith("#"):
            v = "FF" + v[1:]
        out.append(f"--data={k}={v}")
    return out


def rive(args, cwd=PROJECT):
    p = subprocess.run([RIVE, "."] + list(args), cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def shot(path, *steps, fixture=None, data=(), viewport=None, dump=None):
    args = [f"--screenshot={path}"] + fixture_args(fixture) + [f"--data={d}" for d in data]
    if viewport:
        args.append(f"--viewport={viewport}")
    if dump:
        args.append(f"--data-dump={dump}")
    args += list(steps)
    code, log = rive(args)
    if code != 0:
        raise SystemExit(f"rive failed for {path}:\n{log}")
    return log


def click(x, y):
    return [f"--pointer=click@{x},{y}", "--pointer=move@5,5"]


def adv(n):
    return [f"--advance={n}"]
