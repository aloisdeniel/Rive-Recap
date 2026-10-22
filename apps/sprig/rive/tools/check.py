#!/usr/bin/env python3
"""Headless behaviour checks for the Sprig recap (run from apps/sprig/rive: python3 tools/check.py).

The first fourteen run at the design size (390 x 844); the responsive ones lay the artboard out at other
viewports (--viewport, layout fit) and, for the mid-scene resize, drive an instance from a throwaway
harness project (tools/harness/harness.luau, built under build/harness).

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


# ---------------------------------------------------------------- responsive layout

ORIENT_KEYS = ["_vw", "_vh", "_landscape", "_tall", "currentScreen"]


def at_viewport(w, h, *args):
    """View model after `args`, laid out at w x h (the CLI's default layout fit resizes the artboard)."""
    doc = json.loads(subprocess.run([RIVE, PROJ, "--quiet", "--data-dump=-", f"--viewport={w}x{h}"] + list(args),
                                    capture_output=True, text=True, check=True).stdout)
    return {p["path"]: p.get("value") for p in doc["viewModel"]["properties"]}


@check
def orientation_follows_width():
    rows = []
    ok = True
    for w, h, want in ((767, 1024, False), (768, 1024, True), (740, 360, False), (1366, 600, True),
                       (390, 844, False), (820, 1180, True)):
        v = at_viewport(w, h, NO_AUTO, "--advance=4")
        good = v.get("_landscape") is want and v.get("_vw") == w and v.get("_vh") == h
        ok &= good
        rows.append(f"{w}x{h}->{'L' if v.get('_landscape') else 'P'}")
    return ok, " ".join(rows)


@check
def breakpoint_is_tunable():
    v = at_viewport(1024, 768, NO_AUTO, "--data=layoutBreakpoint=1100", "--advance=4")
    v2 = at_viewport(700, 900, NO_AUTO, "--data=layoutBreakpoint=600", "--advance=4")
    ok = v.get("_landscape") is False and v2.get("_landscape") is True
    return ok, f"1024 wide @1100 -> landscape={v.get('_landscape')}; 700 wide @600 -> landscape={v2.get('_landscape')}"


@check
def right_arrow_and_tap_zones_at_other_sizes():
    out = []
    ok = True
    for w, h in ((1280, 720), (740, 360), (320, 568), (820, 1180)):
        v = at_viewport(w, h, NO_AUTO, "--advance=30", "--key=right", "--advance=60", "--key=right", "--advance=60")
        # tap the right two-thirds (next, at its far edge: clear of the hero-leaf hold region) and the left third (back)
        t = at_viewport(w, h, NO_AUTO, "--advance=30", f"--pointer=click@{int(w * 0.97)},{int(h * 0.45)}",
                        "--advance=60", f"--pointer=click@{int(w * 0.97)},{int(h * 0.45)}", "--advance=60",
                        f"--pointer=click@{int(w * 0.12)},{int(h * 0.45)}", "--advance=60")
        good = v.get("currentScreen") == 3 and t.get("currentScreen") == 2
        ok &= good
        out.append(f"{w}x{h}: Right x2->{v.get('currentScreen')}, tap next x2 + back->{t.get('currentScreen')}")
    return ok, "; ".join(out)


@check
def hold_pauses_on_real_width():
    out, ok = [], True
    for w, h in ((1280, 720), (740, 360)):
        x, y = int(w * 0.97), int(h * 0.45)
        v = at_viewport(w, h, "--data=autoAdvanceSeconds=3", "--advance=200", f"--pointer=down@{x},{y}", "--advance=60")
        v2 = at_viewport(w, h, "--data=autoAdvanceSeconds=3", "--advance=200", f"--pointer=down@{x},{y}", "--advance=60",
                         f"--pointer=up@{x},{y}", "--advance=30")
        good = v.get("_holdPaused") is True and v2.get("currentScreen") == 1 and v2.get("_holdPaused") is False
        ok &= good
        out.append(f"{w}x{h}: hold -> paused={v.get('_holdPaused')}, release -> screen {v2.get('currentScreen')}")
    return ok, "; ".join(out)


def build_harness():
    """A throwaway project: scene.rml + a ResizeHarness artboard whose script instances SprigRecap and
    resizes it mid-run (tools/harness/harness.luau). Lives in build/harness, never in the shipped file."""
    import re
    hd = os.path.join(PROJ, "build", "harness")
    shutil.rmtree(hd, ignore_errors=True)
    os.makedirs(os.path.join(hd, "scripts"))
    for f in os.listdir(os.path.join(PROJ, "scripts")):
        shutil.copy(os.path.join(PROJ, "scripts", f), os.path.join(hd, "scripts", f))
    shutil.copy(os.path.join(PROJ, "tools", "harness", "harness.luau"), os.path.join(hd, "scripts", "harness.luau"))
    os.symlink(os.path.join(PROJ, "assets"), os.path.join(hd, "assets"))
    shutil.copy(os.path.join(PROJ, "rive.yaml"), os.path.join(hd, "rive.yaml"))
    src = open(os.path.join(PROJ, "scene.rml")).read()
    head = re.search(r'<Artboard [^>]*name="SprigRecap" id="[^"]+"', src).group(0)
    ab = re.search(r' id="([^"]+)"$', head).group(1)
    vmid = re.search(r'viewModelId="([^"]+)"', head).group(1)
    inst = re.search(r'viewModelInstanceId="([^"]+)"', head).group(1)
    harness = f"""
  <Artboard defaultStateMachineId="0:99010" width="1280" height="900" styleId="0:99002" viewModelId="{vmid}" viewModelInstanceId="{inst}" name="ResizeHarness" id="0:99001" x="2000" y="0">
    <LayoutComponentStyle name="Harness style" id="0:99002"/>
    <ScriptedDrawable scriptAssetId="0:99020" name="Harness" id="0:99003">
      <ScriptInputArtboard artboardId="{ab}" name="recap" id="0:99004"/>
    </ScriptedDrawable>
    <StateMachine name="Harness machine" id="0:99010">
      <StateMachineLayer name="Layer" id="0:99011">
        <AnyState x="200" y="-120"/>
        <ExitState x="400" y="-120"/>
        <EntryState/>
      </StateMachineLayer>
    </StateMachine>
  </Artboard>
  <ScriptAsset file="scripts/harness.luau" name="harness" id="0:99020"/>
"""
    i = src.rindex("</Rive>")
    open(os.path.join(hd, "scene.rml"), "w").write(src[:i] + harness + src[i:])
    return hd


def harness_run(png=None):
    hd = build_harness()
    cmd = [RIVE, hd, "--artboard=ResizeHarness", f"--screenshot={png or os.path.join(hd, 'harness.png')}",
           "--advance=470"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    rows = {}
    for line in (r.stdout + r.stderr).splitlines():
        if "RESIZE " in line:
            parts = line[line.index("RESIZE "):].split()
            rows[parts[1]] = dict(p.split("=", 1) for p in parts[2:] if "=" in p)
    return rows, r


@check
def resize_across_threshold_mid_scene():
    rows, r = harness_run()
    if not all(k in rows for k in "ABCD"):
        return False, f"harness incomplete: {sorted(rows)}; {(r.stdout + r.stderr)[-400:]}"
    A, B, C, M, D = rows["A"], rows["B"], rows["C"], rows["M"], rows["D"]
    ok = (A["cs"] == "2" and A["land"] == "true" and B["cs"] == "2" and B["land"] == "false" and C["cs"] == "2"
          and C["land"] == "false" and C["vw"] == "600.0" and D["cs"] == "3" and D["land"] == "true")
    # the applied placement equals the solved one right after the switch, and the scene is settled (no recede)
    ok &= all(abs(float(X["artx"]) - float(X["artx_solved"])) < 0.05 for X in (B, C, D))
    ok &= abs(float(C["content_scale"]) - 1) < 1e-3 and abs(float(D["content_scale"]) - 1) < 1e-3
    # a mid-scene resize ends in exactly the layout a fresh start at that size has
    s600 = at_viewport(600, 900, NO_AUTO, "--advance=30", "--key=right", "--advance=170")
    s1280 = at_viewport(1280, 800, NO_AUTO, "--advance=30", "--key=right", "--advance=60", "--key=right",
                        "--advance=170")
    diffs = []
    for X, S in ((C, s600), (D, s1280)):
        for k, val in X.items():
            if k.startswith("_l") and k in S and abs(float(val) - float(S[k])) > 0.01:
                diffs.append(f"{k} {val} vs {S[k]}")
    ok &= not diffs
    msg = (f"scene 2 at 1280x800 (landscape) -> 600x900 mid-scene: still scene {C['cs']}, landscape={C['land']}, "
           f"art x {C['artx']} = solved; Continue then resize back mid-transition -> scene {D['cs']}, "
           f"landscape={D['land']}; {len([k for k in C if k.startswith('_l')])} solved values match fresh starts"
           + (f"; DIFF {diffs[:3]}" if diffs else ""))
    return ok, msg


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
