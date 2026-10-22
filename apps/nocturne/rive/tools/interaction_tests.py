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


def run(*flags, project=None):
    cmd = [RIVE, project or ".", "--data-dump=-", "--quiet"] + list(flags)
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
    v = run("--advance=60", "--pointer=drag@135,242>230,330:16", "--advance=30")
    return v["currentScreen"] == 1 and not v["isHolding"], f"screen={v['currentScreen']} holding={v['isHolding']}"


@case
def controls_do_not_trigger_tap_regions():
    v = run("--advance=10", PAUSE, "--advance=10")
    return v["currentScreen"] == 1 and v["isPaused"], f"screen={v['currentScreen']} paused={v['isPaused']}"


@case
def runtime_update_changes_value():
    v = run("--data=observationNights=512", "--advance=10", *taps(NEXT, 1), "--advance=160")
    return v["observationNights"] == 512, "observationNights=512 (see captures/runtime-update.png for the pixels)"


@case
def tab_order_only_visible_controls():
    seen = []
    for n in range(1, 5):
        v = run("--advance=10", *(["--key=tab", "--advance=4"] * n))
        seen.append(int(v["focusedControl"]))
    s = run("--advance=10", "--key=right", "--advance=4", *(["--key=right", "--advance=4"] * 9), "--key=tab", "--advance=4",
            "--key=tab", "--advance=4", "--key=tab", "--advance=4")
    ok = all(f in (1, 2, 3) for f in seen) and set(seen) == {1, 2, 3} and s["focusedControl"] in (1, 2, 3)
    return ok, f"focus after 1..4 Tabs = {seen}; on the summary after 3 Tabs = {int(s['focusedControl'])} (no hidden stops)"


@case
def summary_slots_are_share_and_replay():
    v = run("--advance=10", *taps(NEXT, 9), "--advance=30", NEXT, "--advance=10", AWAY, "--advance=2")
    ok = v["currentScreen"] == 10 and v["primaryA11yLabel"] == "Share" and v["secondaryA11yLabel"] == "Replay"
    a = run("--advance=10", "--advance=30")
    ok = ok and a["primaryA11yLabel"] == "Continue" and a["secondaryA11yLabel"] == "Pause"
    return ok, f"centre press on summary keeps screen={v['currentScreen']}; labels {v['primaryA11yLabel']}/{v['secondaryA11yLabel']} (intro {a['primaryA11yLabel']}/{a['secondaryA11yLabel']})"


# ---------------------------------------------------------------- responsive layout (README "Responsive layout")
VP_L = "--viewport=1280x720"


def near(a, b, eps=0.5):
    return abs(a - b) <= eps


@case
def orientation_follows_width_only():
    got = {}
    for vp in ("767x1024", "768x1024", "667x375", "1280x720", "390x844", "1366x600"):
        v = run(f"--viewport={vp}", "--advance=5")
        got[vp] = (v["isLandscape"], v["isSideBySide"], int(v["layoutWidth"]))
    ok = got["767x1024"][:2] == (False, False) and got["768x1024"][:2] == (True, True) and \
        got["667x375"][:2] == (False, True) and got["1280x720"][:2] == (True, True) and \
        got["390x844"][:2] == (False, False) and got["1366x600"][:2] == (True, True) and \
        all(got[k][2] == int(k.split("x")[0]) for k in got)
    return ok, " ".join(f"{k}:{'L' if a else 'P'}{'/side' if b else ''}" for k, (a, b, _) in got.items())


@case
def breakpoint_is_host_tunable():
    a = run(VP_L, "--data=layoutBreakpoint=1300", "--advance=5")
    b = run("--viewport=700x900", "--data=layoutBreakpoint=600", "--advance=5")
    ok = not a["isLandscape"] and b["isLandscape"]
    return ok, f"1280 wide with breakpoint 1300 -> landscape={a['isLandscape']}; 700 wide with 600 -> {b['isLandscape']}"


@case
def portrait_defaults_reproduce_design():
    v = run("--advance=5")
    keys = dict(layArtX=0, layArtY=0, layArtS=1, layCopyX=0, layCopyY=0, layCopyS=1, layCardY=0, layCardS=1, layNumBox=116,
                layPrimX=195, layPrimY=780, layTapTop=104, layTapH=650, layProgW=334)
    bad = [k for k, want in keys.items() if not near(v[k], want, 0.01)]
    return not bad, "390x844 lays out exactly as the authored design" if not bad else f"differs: {bad}"


@case
def landscape_keyboard_taps_and_rail():
    v0 = run(VP_L, "--advance=5")
    kb = run(VP_L, "--advance=10", *(["--key=right", "--advance=20"] * 3), "--advance=10")
    tp = run(VP_L, "--advance=10", "--pointer=click@1000,400", "--advance=20", "--pointer=move@5,5", "--advance=2",
             "--pointer=click@1000,400", "--advance=20", "--pointer=move@5,5", "--advance=2",
             "--pointer=click@150,400", "--advance=20")
    px, py = int(v0["layPrimX"]), int(v0["layPrimY"])
    sx, sy = int(v0["laySecX"]), int(v0["laySecY"])
    btn = run(VP_L, "--advance=10", f"--pointer=click@{px},{py}", "--advance=20", "--pointer=move@5,5", "--advance=2",
              f"--pointer=click@{sx},{sy}", "--advance=10")
    hold = run(VP_L, "--advance=10", "--pointer=down@900,400", "--advance=60")
    ok = kb["currentScreen"] == 4 and tp["currentScreen"] == 2 and btn["currentScreen"] == 2 and btn["isPaused"] and \
        hold["isHolding"] and hold["currentScreen"] == 1
    return ok, (f"Right x3 -> {kb['currentScreen']}; taps right,right,left -> {tp['currentScreen']}; rail Continue@{px},{py} "
                f"+ Pause -> screen {btn['currentScreen']} paused={btn['isPaused']}; hold -> {hold['isHolding']}")


@case
def tap_zones_span_real_width():
    out = []
    for vp in ("320x568", "1280x720", "2560x1080", "667x375"):
        W, H = (int(x) for x in vp.split("x"))
        v = run(f"--viewport={vp}", "--advance=5")
        zone = v["layTapNextX"] + v["layTapNextW"]
        rail = v["layPrimX"] if v["isSideBySide"] and W / H >= 1.2 else None
        ok = near(v["layTapPrevW"], zone / 3, 1) and (near(zone, W, 1) if rail is None else zone < rail)
        out.append((vp, ok, round(zone)))
    return all(o for _, o, _ in out), " ".join(f"{vp}:zone 0..{z}" for vp, _, z in out)


def _probe_project(spec):
    """A copy of the project generated with NOCTURNE_RESIZE_PROBE: the layout script re-lays out mid-run as if the
    canvas had been resized (the CLI cannot resize a headless run)."""
    import shutil, tempfile
    tmp = tempfile.mkdtemp(prefix="nocturne-resize-")
    for item in ("rive.yaml", "clock.luau", "layout.luau", "scripts", "shaders", "assets", "tools"):
        src = os.path.join(ROOT, item)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, os.path.join(tmp, item))
    os.makedirs(os.path.join(tmp, "rml"))
    env = dict(os.environ, NOCTURNE_RESIZE_PROBE=spec)
    subprocess.run([sys.executable, os.path.join(tmp, "tools", "generate.py")], env=env, check=True, capture_output=True)
    shutil.rmtree(os.path.join(tmp, "fixtures"), ignore_errors=True)
    return tmp


@case
def resize_across_threshold_mid_scene():
    # landscape 1280 -> portrait 700 wide while scene 3 is showing, and again in the middle of the 3 -> 4 iris
    import shutil
    projects = [_probe_project("6.0:700x900"), _probe_project("5.4:700x900"), _probe_project("6.0:1280x720:700x900")]
    try:
        a = run("--viewport=1280x900", "--advance=10", "--key=right", "--advance=150", "--key=right", "--advance=200",
                "--advance=240", project=projects[0])
        # the Right press lands at 5.17 s; at 5.4 s the stage iris is shut over the 3 -> 4 cut
        b = run("--viewport=1280x900", "--advance=10", "--key=right", "--advance=150", "--key=right", "--advance=150",
                "--key=right", "--advance=170", project=projects[1])
        c = run("--viewport=1280x900", "--advance=10", "--key=right", "--advance=150", "--key=right", "--advance=200",
                "--advance=240", project=projects[2])
        before = run("--viewport=1280x900", "--advance=10", "--key=right", "--advance=150", "--key=right", "--advance=30",
                     project=projects[2])
        before_a = run("--viewport=1280x900", "--advance=10", "--key=right", "--advance=150", "--key=right", "--advance=30",
                       project=projects[0])
    finally:
        for pr in projects:
            shutil.rmtree(pr, ignore_errors=True)

    def settled(v, screen, land):
        return v["currentScreen"] == screen and v["motifPose"] == screen and v["isLandscape"] == land and \
            near(v["layHeroX"], v["layArtX"], 0.01) and near(v["layHeroS"], v["layArtS"], 0.001)
    ok = settled(a, 3, False) and settled(b, 4, False) and settled(c, 3, True) and \
        before["isLandscape"] is False and before_a["isLandscape"] is True
    return ok, (f"L->P on scene 3: screen={a['currentScreen']} pose={a['motifPose']} landscape={a['isLandscape']}; "
                f"mid-iris 3->4: screen={b['currentScreen']} pose={b['motifPose']}; P->L: screen={c['currentScreen']} "
                f"landscape={c['isLandscape']}; hero frame settled on the art frame")


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
