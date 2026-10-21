#!/usr/bin/env python3
"""Headless behaviour checks for the Sprig recap (run from apps/sprig/rive: python3 tools/check.py).

Each check drives the built scene with the CLI (--key / --pointer / --advance / --data) and reads the
bound view model back with --data-dump. Exit status 1 if any check fails.
"""
import json
import os
import shutil
import subprocess
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIVE = shutil.which("rive") or os.path.expanduser("~/.rive/bin/rive")
NEXT, PREV, PAUSE, REPLAY = "195,790", "48,790", "342,790", "342,790"


def run(*args, every=None):
    cmd = [RIVE, PROJ, "--quiet", "--data-dump=-"]
    if every:
        cmd.append(f"--data-dump-every={every}")
    cmd += list(args)
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def final(*args):
    """View model values after the input script, as {path: value}."""
    doc = json.loads(run(*args))
    return {p["path"]: p.get("value") for p in doc["viewModel"]["properties"]}


def series(path, *args, every=1):
    """[(frame, value)] for every frame, forward-filled (the stream only lists changes)."""
    rows = [json.loads(l) for l in run(*args, every=every).splitlines() if l.startswith("{")]
    changes = {}
    last = 0
    for r in rows:
        if "frame" not in r:
            continue
        last = max(last, r["frame"])
        for v in r.get("values", []):
            if v["path"] == path:
                changes[r["frame"]] = v["value"]
    out, cur = [], None
    for f in range(last + 1):
        cur = changes.get(f, cur)
        out.append((f, cur))
    return out


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


NO_AUTO = "--data=autoAdvanceEnabled=false"


@check
def right_key_advances():
    v = final(NO_AUTO, "--advance=30", "--key=right", "--advance=60", "--key=right", "--advance=60")
    return v.get("currentScreen") == 3, f"Right x2 -> {v.get('currentScreen')} (want 3)"


@check
def left_key_goes_back():
    v = final(NO_AUTO, "--advance=30", "--key=right", "--advance=60", "--key=right", "--advance=60", "--key=left",
              "--advance=60")
    return v.get("currentScreen") == 2, f"Right x2, Left -> {v.get('currentScreen')} (want 2)"


@check
def hidden_scenes_are_skipped():
    v = final(NO_AUTO, "--data=showScreen3=false", "--data=showScreen4=false", "--advance=30", "--key=right",
              "--advance=60", "--key=right", "--advance=60")
    return v.get("currentScreen") == 5, f"3,4 hidden, Right x2 -> {v.get('currentScreen')} (want 5)"


@check
def hidden_scenes_skipped_backwards():
    v = final(NO_AUTO, "--data=showScreen3=false", "--data=showScreen4=false", "--advance=30", "--key=right",
              "--advance=60", "--key=right", "--advance=60", "--key=left", "--advance=60")
    return v.get("currentScreen") == 2, f"from 5, Left -> {v.get('currentScreen')} (want 2)"


@check
def rapid_taps_land_on_summary():
    args = [NO_AUTO, "--advance=30"]
    for _ in range(12):
        args += [f"--pointer=click@{NEXT}", "--advance=4"]
    v = final(*args, "--advance=120")
    return v.get("currentScreen") == 10, f"12 rapid Continue clicks -> {v.get('currentScreen')} (want 10)"


@check
def auto_advance_after_settle_plus_dwell():
    s = series("currentScreen", "--data=autoAdvanceSeconds=3", "--advance=330", every=1)
    first2 = next((f for f, v in s if v == 2), None)
    ok = first2 is not None and 285 <= first2 <= 300
    return ok, f"first frame on scene 2 = {first2} (want ~288: 1.8 s settle + 3 s dwell)"


@check
def dwell_is_clamped():
    s = series("currentScreen", "--data=autoAdvanceSeconds=0.5", "--advance=330", every=1)
    first2 = next((f for f, v in s if v == 2), None)
    ok = first2 is not None and 285 <= first2 <= 300
    return ok, f"autoAdvanceSeconds=0.5 -> scene 2 at frame {first2} (clamped to 3 s, want ~288)"


@check
def auto_advance_disabled_holds():
    v = final(NO_AUTO, "--advance=900")
    return v.get("currentScreen") == 1 and v.get("screenProgress") == 0, \
        f"autoAdvanceEnabled=false for 15 s -> screen {v.get('currentScreen')}, progress {v.get('screenProgress')}"


@check
def pause_freezes_progress_exactly():
    s = series("screenProgress", "--data=autoAdvanceSeconds=3", "--advance=200", f"--pointer=click@{PAUSE}",
               "--advance=120", every=1)
    vals = [v for f, v in s if 206 <= f <= 318]
    ok = len(vals) > 50 and max(vals) - min(vals) < 1e-6
    return ok, f"progress while paused spans {min(vals):.4f}..{max(vals):.4f}"


@check
def pause_resumes_from_same_point():
    s = series("screenProgress", "--data=autoAdvanceSeconds=3", "--advance=200", f"--pointer=click@{PAUSE}",
               "--advance=120", f"--pointer=click@{PAUSE}", "--advance=20", every=1)
    paused = [v for f, v in s if 220 <= f <= 318][-1]
    after = [v for f, v in s if f >= 330][-1]
    ok = 0 < after - paused < 0.15
    return ok, f"paused at {paused:.4f}, 0.2 s after resume {after:.4f}"


@check
def summary_never_auto_advances():
    args = ["--data=autoAdvanceSeconds=3", "--advance=30"]
    for _ in range(9):
        args += [f"--pointer=click@{NEXT}", "--advance=30"]
    v = final(*args, "--advance=600")
    return v.get("currentScreen") == 10 and v.get("screenProgress") == 0, \
        f"10 s on summary -> screen {v.get('currentScreen')}, progress {v.get('screenProgress')}"


@check
def replay_returns_to_intro():
    args = [NO_AUTO, "--advance=30"]
    for _ in range(9):
        args += [f"--pointer=click@{NEXT}", "--advance=30"]
    v = final(*args, "--advance=120", f"--pointer=click@{REPLAY}", "--advance=120")
    return v.get("currentScreen") == 1, f"Replay -> {v.get('currentScreen')} (want 1)"


@check
def space_toggles_pause():
    v = final(NO_AUTO, "--advance=30", "--key=space", "--advance=10")
    return v.get("isPaused") is True, f"Space -> isPaused={v.get('isPaused')}"


@check
def hold_pauses_and_release_does_not_navigate():
    v = final("--data=autoAdvanceSeconds=3", "--advance=200", "--pointer=down@300,400", "--advance=60")
    held = v.get("_holdPaused")
    v2 = final("--data=autoAdvanceSeconds=3", "--advance=200", "--pointer=down@300,400", "--advance=60",
               "--pointer=up@300,400", "--advance=30")
    ok = held is True and v2.get("currentScreen") == 1 and v2.get("_holdPaused") is False
    return ok, f"hold -> _holdPaused={held}; release -> screen {v2.get('currentScreen')}, held={v2.get('_holdPaused')}"


def main():
    failed = 0
    for fn in CHECKS:
        try:
            ok, msg = fn()
        except Exception as e:  # noqa
            ok, msg = False, f"error: {e}"
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {fn.__name__}: {msg}")
    print(f"{len(CHECKS) - failed}/{len(CHECKS)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
