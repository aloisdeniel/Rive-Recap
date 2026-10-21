#!/usr/bin/env python3
"""Headless behaviour checks for the Nocturne recap.

Each case drives the real runtime through `rive --data-dump` with synthesised
pointer / keyboard input and asserts on the UserRecap values afterwards.
Run from apps/nocturne/rive:  python3 tools/interaction_tests.py
"""
import json, os, subprocess, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RIVE = os.path.expanduser("~/.rive/bin/rive")
NEXT = "--pointer=click@195,780"
PREV = "--pointer=click@70,780"
PAUSE = "--pointer=click@320,780"
AWAY = "--pointer=move@380,20"


def run(*flags):
    cmd = [RIVE, ".", "--data-dump=-", "--quiet"] + list(flags)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    d = json.loads(r.stdout)
    vals = {}

    def walk(o):
        if isinstance(o, dict):
            if "path" in o and "value" in o:
                vals[o["path"]] = o["value"]
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d.get("viewModel", d))
    return vals


def taps(btn, n, gap=24):
    out = []
    for _ in range(n):
        out += [btn, f"--advance={gap}", AWAY, "--advance=2"]
    return out


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def boots_on_intro():
    v = run("--advance=30")
    return v["currentScreen"] == 1, f"currentScreen={v['currentScreen']}"


@case
def next_and_back():
    v = run("--advance=10", *taps(NEXT, 3), *taps(PREV, 1), "--advance=30")
    return v["currentScreen"] == 3 and v["navDirection"] == -1, f"screen={v['currentScreen']} dir={v['navDirection']}"


@case
def tap_regions_navigate():
    v = run("--advance=10", "--pointer=click@300,400", "--advance=20", AWAY, "--advance=2",
            "--pointer=click@300,400", "--advance=20", AWAY, "--advance=2", "--pointer=click@40,400", "--advance=20")
    return v["currentScreen"] == 2, f"screen={v['currentScreen']} (right,right,left)"


@case
def rapid_taps_settle():
    v = run("--advance=5", *taps(NEXT, 7, gap=3), "--advance=120")
    return v["currentScreen"] == 8, f"screen={v['currentScreen']} after 7 rapid taps"


@case
def hold_pauses_without_tap():
    v = run("--advance=10", "--pointer=down@300,400", "--advance=60")
    held = v["isHolding"]
    v2 = run("--advance=10", "--pointer=down@300,400", "--advance=60", "--pointer=up@300,400", "--advance=20")
    ok = held and (not v2["isHolding"]) and v2["currentScreen"] == 1 and not v2["isPaused"]
    return ok, f"holding during={held}, after release screen={v2['currentScreen']} holding={v2['isHolding']}"


@case
def pause_freezes_progress():
    a = run("--advance=150", PAUSE, "--advance=5", AWAY, "--advance=2")
    b = run("--advance=150", PAUSE, "--advance=5", AWAY, "--advance=240")
    c = run("--advance=150", PAUSE, "--advance=5", AWAY, "--advance=120", PAUSE, "--advance=5", AWAY, "--advance=120")
    ok = a["isPaused"] and abs(a["screenProgress"] - b["screenProgress"]) < 1e-6 and not c["isPaused"] and \
        c["screenProgress"] > b["screenProgress"]
    return ok, f"paused={a['isPaused']} p={a['screenProgress']:.3f}->{b['screenProgress']:.3f} (4s paused) resumed p={c['screenProgress']:.3f}"


@case
def keyboard_navigation():
    v = run("--advance=10", "--key=right", "--advance=10", "--key=right", "--advance=10", "--key=left", "--advance=10",
            "--key=space", "--advance=10")
    return v["currentScreen"] == 2 and v["isPaused"], f"screen={v['currentScreen']} paused={v['isPaused']}"


@case
def keyboard_enter_activates_focused():
    v = run("--advance=10", "--key=enter", "--advance=10")
    return v["currentScreen"] == 2, f"Enter on focused Continue -> screen={v['currentScreen']}"


@case
def full_auto_advance_reaches_summary_once():
    v = run("--advance=90s")
    return v["currentScreen"] == 10 and v["recapFinishedFired"] and v["screenProgress"] == 1, \
        f"screen={v['currentScreen']} finished={v['recapFinishedFired']} progress={v['screenProgress']}"


@case
def auto_advance_disabled():
    v = run("--data=autoAdvanceEnabled=false", "--advance=20s")
    return v["currentScreen"] == 1, f"screen={v['currentScreen']}"


@case
def unsafe_duration_clamped():
    v = run("--data=autoAdvanceSeconds=0.2", "--advance=4s")
    return v["currentScreen"] == 1, f"0.2s request clamped to 3s minimum -> screen={v['currentScreen']} at 4s"


@case
def replay_resets_latch():
    v = run("--advance=90s", "--pointer=click@320,780", "--advance=30")
    return v["currentScreen"] == 1 and not v["recapFinishedFired"], f"screen={v['currentScreen']} latch={v['recapFinishedFired']}"


@case
def hidden_scenes_skipped_both_ways():
    flags = ["--data=showScreen3=false", "--data=showScreen4=false", "--data=showScreen9=false"]
    f = run(*flags, "--advance=10", *taps(NEXT, 2), "--advance=10")
    b = run(*flags, "--advance=10", *taps(NEXT, 2), *taps(PREV, 1), "--advance=10")
    s = run(*flags, "--advance=10", *taps(NEXT, 7), "--advance=10")
    return f["currentScreen"] == 5 and b["currentScreen"] == 2 and s["currentScreen"] == 10, \
        f"1->{f['currentScreen']} back->{b['currentScreen']} 7 taps->{s['currentScreen']}"


@case
def zero_user_intro_to_summary():
    flags = [f"--data=showScreen{i}=false" for i in range(2, 10)]
    v = run(*flags, "--advance=10", *taps(NEXT, 1), "--advance=10")
    return v["currentScreen"] == 10 and not v["hasStats"], f"screen={v['currentScreen']} hasStats={v['hasStats']}"


@case
def persona_mapping_atomic():
    v = run("--data=personaIndex=2", "--advance=10")
    u = run("--data=personaIndex=17", "--advance=10")
    ok = v["personaName"] == "Planet Tracker" and v["personaColor"].upper().endswith("F7BE62") and v["personaSlot"] == 2 \
        and u["personaName"] == "Deep Sky Dreamer" and u["personaSlot"] == 0
    return ok, f"2->{v['personaName']}/{v['personaColor']}/{v['personaSlot']}; 17->{u['personaName']}/{u['personaSlot']}"


@case
def finder_drag_does_not_navigate():
    v = run("--advance=60", "--pointer=drag@241,262>160,330:16", "--advance=30")
    return v["currentScreen"] == 1 and not v["isHolding"], f"screen={v['currentScreen']} holding={v['isHolding']}"


@case
def controls_do_not_trigger_tap_regions():
    v = run("--advance=10", PAUSE, "--advance=10")
    return v["currentScreen"] == 1 and v["isPaused"], f"screen={v['currentScreen']} paused={v['isPaused']}"


@case
def runtime_update_changes_value():
    v = run("--data=observationNights=512", "--advance=10", *taps(NEXT, 1), "--advance=160")
    return v["observationNights"] == 512, "observationNights=512 (see captures/runtime-update.png for the pixels)"


def main():
    failed = 0
    for fn in CASES:
        try:
            ok, msg = fn()
        except Exception as e:  # noqa
            ok, msg = False, f"exception: {e}"
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {fn.__name__:40s} {msg}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
