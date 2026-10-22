#!/usr/bin/env python3
"""Behavioural checks for the Crux recap, run headless through `rive --data-dump`.

    python3 tools/verify.py        # from apps/crux/rive

Each scenario drives the real .riv (pointer, keyboard, data) and asserts on the
UserRecap values the director and state machines write back. Results are also
saved to captures/data/verify-report.json.
"""
import json
import os
import shutil
import subprocess

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RIVE = os.path.expanduser("~/.rive/bin/rive")
TAP_NEXT = "--pointer=click@300,400"
TAP_BACK = "--pointer=click@60,400"


def dump(args, every=None):
    cmd = [RIVE, ROOT, "--quiet", "--data-dump=-"] + list(args)
    if every:
        cmd.insert(3, f"--data-dump-every={every}")
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    if every:
        return [json.loads(l) for l in out.splitlines() if l.strip()]
    d = json.loads(out)
    return {p["path"]: p.get("value", p.get("changed")) for p in d["viewModel"]["properties"]}


def series(lines, key):
    out = []
    for l in lines:
        for v in l.get("values", []):
            if v["path"] == key:
                out.append((round(l.get("time", 0), 3), v.get("value", v.get("fired"))))
    return out


RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append({"check": name, "pass": bool(cond), "detail": str(detail)})
    print(("PASS " if cond else "FAIL ") + name, detail)


# ------------------------------------------------------------------ responsive layout
PORTRAIT = ["320x568", "360x640", "390x844", "430x932", "600x960", "767x1024", "667x375", "740x360"]
LANDSCAPE = ["768x1024", "820x1180", "1024x768", "1280x720", "1440x900", "1920x1080", "2560x1080", "1366x600"]
# minimum on-screen scale per block kind: 14 pt copy >= ~10.5 pt, 16-18 pt unit labels >= 10 pt
FLOOR = {"copy": 0.75, "title": 0.72, "head": 0.62, "ehead": 0.75, "hero": 0.55, "dial": 0.6}


def rig_dump(args, viewport=None):
    cmd = [RIVE, ROOT, "--quiet", "--data-dump=-"] + ([f"--viewport={viewport}"] if viewport else []) + list(args)
    d = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
    vm = {p["path"]: p.get("value") for p in d["viewModel"]["properties"]}
    g = {}
    for gl in d.get("globals", []):
        g.update({p["path"]: p.get("value") for p in gl["properties"]})
    return vm, g


def placed(g, W, H):
    """Screen-space boxes of every block, from the rig values and tools/rig.py."""
    import rig
    k = g["k"]
    wide = g["wide"]
    out = {}
    for sk, sc in rig.S.items():
        for name, b in sc["blocks"].items():
            bx, by, bs = (g[n] * k for n in rig.block_names(sk, name))
            box = [a + (c - a) * wide for a, c in zip(b["box"], b["wbox"])]
            out[(sk, name)] = (bx + box[0] * bs, by + box[1] * bs, bx + (box[0] + box[2]) * bs,
                               by + (box[1] + box[3]) * bs, bs)
    return out


def responsive():
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    # 13. orientation is a pure width rule, re-derived from the real artboard size
    modes = {}
    for vp in PORTRAIT + LANDSCAPE:
        vm, g = rig_dump(["--data=currentScreen=2", "--advance=3"], vp)
        modes[vp] = (g["landscape"], g["mode"], g, vm)
    bad = [vp for vp in PORTRAIT if modes[vp][0] != 0] + [vp for vp in LANDSCAPE if modes[vp][0] != 1]
    check("landscape exactly when width >= 768 (16 sizes, incl. 767x1024 / 768x1024)", not bad, bad)
    folds = [vp for vp in PORTRAIT if modes[vp][1] == 1]
    check("short portrait canvases fold into columns (667x375, 740x360)", set(folds) == {"667x375", "740x360"}, folds)
    vm, g = rig_dump(["--data=layoutBreakpoint=1300", "--advance=3"], "1280x720")
    vm2, g2 = rig_dump(["--data=layoutBreakpoint=1024", "--advance=3"], "1024x768")
    check("layoutBreakpoint is tunable by the host (1300 -> 1280 wide is portrait; 1024 -> 1024 is landscape)",
          g["landscape"] == 0 and g2["landscape"] == 1 and vm["layoutBreakpoint"] == 1300, (g["landscape"], g2["landscape"]))
    # 14. controls and readable sizes at every size
    small = []
    floors = []
    overlaps = []
    for vp, (_, mode, g, _) in modes.items():
        W, H = map(int, vp.split("x"))
        if g["btn"] < 44 or g["pill"] < 44:
            small.append((vp, g["btn"], g["pill"]))
        boxes = placed(g, W, H)
        for (sk, name), (x0, y0, x1, y1, bs) in boxes.items():
            if name in FLOOR and bs < FLOOR[name] - 1e-3:
                floors.append((vp, sk, name, round(bs, 2)))
        if mode != 0:
            # wide modes: blocks of one arrangement never overlap and stay inside the
            # canvas, between the top bar and the controls
            import rig
            for sk, sc in rig.S.items():
                if sk == 10:
                    groups = [["head", "card"], ["ehead", "eart"]]
                else:
                    groups = [[n for n in sc["blocks"]]]
                for grp in groups:
                    for i, a in enumerate(grp):
                        A = boxes[(sk, a)]
                        if A[0] < -1 or A[2] > W + 1 or A[1] < g["topH"] - 1 or A[3] > H - g["botH"] + 1:
                            overlaps.append((vp, sk, a, "outside", [round(v) for v in A[:4]]))
                        for b in grp[i + 1:]:
                            Bb = boxes[(sk, b)]
                            if A[0] < Bb[2] - 1 and Bb[0] < A[2] - 1 and A[1] < Bb[3] - 1 and Bb[1] < A[3] - 1:
                                overlaps.append((vp, sk, a, b))
    check("controls are at least 44 x 44 at every size", not small, small)
    check("copy, titles and unit labels never fall below their readable scale floor", not floors, floors[:6])
    check("wide layouts: blocks never overlap, stay inside the canvas and clear the controls", not overlaps, overlaps[:6])
    # 15. tap zones, hold and keyboard use the real width
    v = dump_vp("1280x720", ["--data=currentScreen=4", "--advance=60", "--pointer=click@400,360", "--advance=10"])
    check("1280x720: a tap at x=400 (< 1280/3) goes back", v["currentScreen"] == 3, v["currentScreen"])
    v = dump_vp("1280x720", ["--data=currentScreen=4", "--advance=60", "--pointer=click@460,360", "--advance=10"])
    check("1280x720: a tap at x=460 (> 1280/3) advances", v["currentScreen"] == 5, v["currentScreen"])
    v = dump_vp("1920x1080", ["--data=currentScreen=3", "--advance=130", "--pointer=down@1200,500", "--advance=40"])
    check("1920x1080: hold pauses", v["isPaused"] is True and v["currentScreen"] == 3, (v["isPaused"], v["currentScreen"]))
    v = dump_vp("1280x720", ["--advance=30", "--key=right", "--advance=5", "--key=right", "--advance=5"])
    check("1280x720: Right arrow advances scenes", v["currentScreen"] == 3, v["currentScreen"])
    v = dump_vp("740x360", ["--advance=30", "--key=right", "--advance=5"])
    check("740x360: Right arrow advances scenes", v["currentScreen"] == 2, v["currentScreen"])
    v = dump_vp("1280x720", ["--data=currentScreen=1", "--advance=120", "--pointer=drag@" + grab_point("1280x720") + ":10",
                             "--advance=30"])
    check("1280x720: dragging the relocated hold does not navigate", v["currentScreen"] == 1, v["currentScreen"])
    # 16. resizing across the breakpoint mid-scene and mid-transition (harness artboard)
    harness_checks()


def dump_vp(vp, args):
    return dump([f"--viewport={vp}"] + list(args))


def grab_point(vp):
    """Where the scene-1 hold sits at this size (its block transform), and a drag from it."""
    import rig
    _, g = rig_dump(["--data=currentScreen=1", "--advance=3"], vp)
    k = g["k"]
    x = (g["s1ArtX"] + g["s1ArtS"] * 115) * k
    y = (g["s1ArtY"] + g["s1ArtS"] * 605) * k
    return f"{x:.0f},{y:.0f}>{x + 90:.0f},{y - 80:.0f}"


HARNESS = """<Rive version="1" kind="fragment">
<Artboard defaultStateMachineId="0:99001" viewModelId="{vm}" viewModelInstanceId="{inst}" width="1200" height="900" styleId="0:99002" name="Harness" id="0:99000">
  <LayoutComponentStyle name="Harness Style" id="0:99002"/>
  <NestedArtboardLayout artboardId="0:20" instanceWidth="390" instanceHeight="844" name="Recap" id="0:99003">
    <NestedStateMachine animationId="0:21" name="Recap SM"/>
  </NestedArtboardLayout>
  <StateMachine name="Resize" id="0:99001">
    <StateMachineLayer name="L" id="0:99004"><AnyState x="0" y="-100"/><ExitState x="200" y="-100"/>
      <EntryState><StateTransition stateToId="0:99005"/></EntryState>
      <AnimationState animationId="0:99006" x="200" y="0" id="0:99005"/></StateMachineLayer>
  </StateMachine>
  <LinearAnimation duration="{dur}" name="Resize" id="0:99006">
    <KeyedObject objectId="0:99003">
      <KeyedProperty propertyKey="663">{w}</KeyedProperty>
      <KeyedProperty propertyKey="664">{h}</KeyedProperty>
    </KeyedObject>
  </LinearAnimation>
</Artboard>
</Rive>
"""


def harness(name, sizes):
    """A temporary copy of the project with an extra artboard that nests the recap in a
    layout whose size is keyed: sizes = [(frame, w, h)]. Returns the project path."""
    import model
    dst = os.path.join(ROOT, "build", "harness-" + name)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    for f in os.listdir(ROOT):
        if f.endswith((".luau", ".wgsl")) or f == "rive.yaml":
            shutil.copy(os.path.join(ROOT, f), dst)
    shutil.copytree(os.path.join(ROOT, "scene"), os.path.join(dst, "scene"))
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(dst, "assets"))
    kf = lambda i: "".join(f'<KeyFrameDouble value="{s[i]}" frame="{s[0]}" interpolationType="hold"/>' for s in sizes)
    with open(os.path.join(dst, "scene", "5-harness.rml"), "w") as f:
        f.write(HARNESS.format(vm=model.VM_ID, inst=model.DEFAULT_INSTANCE, dur=sizes[-1][0] + 60, w=kf(1), h=kf(2)))
    return dst


def harness_series(project, data, seconds, every=6):
    cmd = [RIVE, project, "--quiet", "--artboard=Harness", "--viewport=1200x900", f"--data-dump-every={every}",
           "--data-dump=-"] + [f"--data={d}" for d in data] + [f"--advance={seconds}s"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def harness_checks():
    # A: settled scene 3, portrait 390x844 -> landscape 1100x700 at 3 s
    p = harness("a", [(0, 390, 844), (180, 1100, 700)])
    lines = harness_series(p, ["currentScreen=3", "autoAdvanceEnabled=false"], 5)
    land = series(lines, "globals/CruxRig/landscape")
    cs = series(lines, "currentScreen")
    sig = [x for x in series(lines, "screenSignal") if x[1]]
    wide = series(lines, "globals/CruxRig/wide")
    settled = series(lines, "sceneSettled")
    ent = series(lines, "enteredScreen")
    check("resize 390x844 -> 1100x700 mid-scene flips to landscape", land and land[-1][1] == 1 and
          any(v == 0 for t, v in land), land)
    check("... keeps scene 3, fires no screenChanged, stays settled", cs[-1][1] == 3 and not sig and settled[-1][1] is True
          and ent[-1][1] == 3, (cs[-1], len(sig), settled[-1], ent[-1]))
    t_switch = next((t for t, v in land if v == 1), 99)
    done = next((t for t, v in wide if v == 1 and t > t_switch), None)
    check("... eases into the landscape arrangement within 0.5 s", done is not None and done - t_switch <= 0.55,
          (t_switch, done))
    # B: auto-advance 2 -> 3 starts at ~4.8 s; resize to landscape mid-transition (5.0 s), back to portrait at 7 s
    p = harness("b", [(0, 390, 844), (300, 1100, 700), (420, 600, 900)])
    lines = harness_series(p, ["currentScreen=2", "autoAdvanceSeconds=3"], 9.5)
    cs = series(lines, "currentScreen")
    ent = series(lines, "enteredScreen")
    sig = [x for x in series(lines, "screenSignal") if x[1]]
    land = series(lines, "globals/CruxRig/landscape")
    t_nav = next((t for t, v in cs if v == 3), None)
    check("resize across the threshold mid-transition (2 -> 3 yank in flight)", t_nav is not None and 4.5 < t_nav < 5.1
          and [v for t, v in land][-1] == 0 and any(v == 1 for t, v in land), (t_nav, land))
    check("... settles cleanly on scene 3 (entered == current, one signal)", cs[-1][1] == 3 and ent[-1][1] == 3 and
          len(sig) == 1, (cs[-1], ent[-1], len(sig)))
    car = series(lines, "globals/CruxRig/carS")
    check("... the carrier space follows the entered scene", car and car[-1][1] > 0, car[-1:])
    shutil.rmtree(os.path.join(ROOT, "build", "harness-a"), ignore_errors=True)
    shutil.rmtree(os.path.join(ROOT, "build", "harness-b"), ignore_errors=True)


def main():
    # 1. tap right advances, tap left goes back
    v = dump(["--advance=60", TAP_NEXT, "--advance=10"])
    check("tap right two-thirds advances", v["currentScreen"] == 2, v["currentScreen"])
    v = dump(["--data=currentScreen=4", "--advance=60", TAP_BACK, "--advance=10"])
    check("tap left third goes back", v["currentScreen"] == 3 and v["navDirection"] == -1, (v["currentScreen"], v["navDirection"]))
    # 2. rapid taps settle on the final requested scene, one signal per change
    taps = ["--advance=30"]
    for _ in range(5):
        taps += [TAP_NEXT, "--pointer=move@10,300"]
    lines = dump(taps + ["--advance=3s"], every=1)
    cs = series(lines, "currentScreen")
    ent = series(lines, "enteredScreen")
    check("rapid taps reach scene 6", cs[-1][1] == 6, cs)
    check("rapid taps settle (entered == current)", ent[-1][1] == 6, ent[-4:])
    sig = [x for x in series(lines, "screenSignal") if x[1]]
    check("one screenSignal per scene change", len(sig) == 5, len(sig))
    # 3. hold pauses, release restores and does not navigate
    v = dump(["--data=currentScreen=3", "--advance=130", "--pointer=down@300,400", "--advance=40"])
    check("hold pauses", v["isPaused"] is True and v["currentScreen"] == 3, (v["isPaused"], v["currentScreen"]))
    v = dump(["--data=currentScreen=3", "--advance=130", "--pointer=down@300,400", "--advance=40",
              "--pointer=up@300,400", "--advance=10"])
    check("release resumes without a tap", v["isPaused"] is False and v["currentScreen"] == 3, (v["isPaused"], v["currentScreen"]))
    # 4. pause freezes progress, resume continues from the same point
    lines = dump(["--data=currentScreen=2", "--advance=3s", "--pointer=click@108,783", "--advance=2s",
                  "--pointer=move@200,300", "--pointer=click@108,783", "--advance=1s"], every=6)
    prog = series(lines, "screenProgress")
    paused = series(lines, "isPaused")
    frozen = [p for t, p in prog if 3.2 < t < 5.0]
    vals = [x[1] for x in paused]
    check("pause button toggles isPaused", True in vals and vals[vals.index(True) + 1:].count(False) >= 1, paused)
    check("progress frozen while paused (no progress writes 3.2-5.0 s)", len(frozen) == 0, frozen[:3])
    check("progress resumes after play", prog[-1][1] > (frozen[0] if frozen else 0), prog[-1])
    # 5. hidden scenes are skipped in both directions; segments adapt
    hide = ["--data=showScreen3=false", "--data=showScreen4=false"]
    v = dump(hide + ["--data=currentScreen=2", "--advance=60", TAP_NEXT, "--advance=10"])
    check("forward skips hidden 3,4", v["currentScreen"] == 5 and v["visibleScreenCount"] == 8, (v["currentScreen"], v["visibleScreenCount"]))
    v = dump(hide + ["--data=currentScreen=5", "--advance=60", TAP_BACK, "--advance=10"])
    check("back skips hidden 4,3", v["currentScreen"] == 2 and v["visibleScreenPosition"] == 2, (v["currentScreen"], v["visibleScreenPosition"]))
    # 6. invalid visibility -> safe intro/summary path; zero user gets the welcome summary
    allhide = [f"--data=showScreen{i}=false" for i in range(1, 11)]
    v = dump(allhide + ["--advance=30", TAP_NEXT, "--advance=10"])
    check("all flags false still yields intro -> summary", v["currentScreen"] == 10 and v["visibleScreenCount"] == 2
          and v["isEmptyRecap"] is True, (v["currentScreen"], v["visibleScreenCount"], v["isEmptyRecap"]))
    v = dump(["--data=currentScreen=7", "--data=showScreen7=false", "--advance=10"])
    check("starting on a hidden scene snaps to the next visible", v["currentScreen"] == 8, v["currentScreen"])
    # 7. replay resets progress and the completion latch
    lines = dump(["--data=currentScreen=10", "--advance=3s", "--pointer=click@108,783", "--advance=3s",
                  "--pointer=move@300,300", TAP_NEXT, "--advance=1s"], every=6)
    fin = [x for x in series(lines, "finishSignal") if x[1]]
    cs = series(lines, "currentScreen")
    check("recapFinished signal fires once on settle", len(fin) == 1, fin)
    check("replay returns to scene 1", any(c == 1 for _, c in cs), cs)
    lines = dump(["--data=currentScreen=10", "--data=autoAdvanceSeconds=3", "--advance=3s", "--pointer=click@108,783",
                  "--advance=60s"], every=30)
    fin = [x for x in series(lines, "finishSignal") if x[1]]
    check("after replay, a full auto-advance run finishes again (latch reset)", len(fin) == 2, fin)
    # 8. auto-advance clamps unsafe durations, disabled auto-advance never moves
    lines = dump(["--data=autoAdvanceSeconds=0.2", "--advance=6s"], every=6)
    cs = series(lines, "currentScreen")
    t2 = next((t for t, c in cs if c == 2), None)
    check("0.2 s dwell is clamped to 3 s readable minimum", t2 is not None and t2 >= 4.5, t2)
    v = dump(["--data=autoAdvanceEnabled=false", "--advance=20s"])
    check("autoAdvanceEnabled=false never advances", v["currentScreen"] == 1, v["currentScreen"])
    # 9. keyboard
    v = dump(["--advance=30", "--key=right", "--advance=5", "--key=right", "--advance=5", "--key=left", "--advance=5"])
    check("Right/Right/Left -> scene 2", v["currentScreen"] == 2, v["currentScreen"])
    v = dump(["--advance=30", "--key=space", "--advance=5"])
    check("Space toggles pause", v["isPaused"] is True, v["isPaused"])
    v = dump(["--advance=30", "--key=tab", "--advance=3"])
    check("Tab moves visible focus to the first control (Previous)", v["focusedControl"] == 1, v["focusedControl"])
    v = dump(["--advance=30", "--key=tab", "--advance=3", "--key=tab", "--advance=3", "--key=enter", "--advance=5"])
    check("Tab, Tab, Enter activates Pause", v["focusedControl"] == 2 and v["isPaused"] is True,
          (v["focusedControl"], v["isPaused"]))
    # 10. runtime data updates + persona mapping + formatting + clamping
    v = dump(["--data=personaIndex=2", "--data=currentScreen=9", "--advance=60"])
    check("persona 2 maps name/line/colour atomically", v["personaName"] == "Balance Seeker" and v["personaSlot"] == 2
          and v["personaColor"].upper().endswith("385DF4"), (v["personaName"], v["personaColor"]))
    v = dump(["--data=personaIndex=9", "--advance=10"])
    check("unknown persona index falls back to row 0", v["personaSlot"] == 0 and v["personaName"] == "Route Reader", v["personaName"])
    v = dump(["--data=sessions=-5", "--data=attempts=1234567", "--data=locale=fr-FR", "--advance=10"])
    check("negative count clamped to 0", v["sessions"] == 0 and v["sessionsDisplay"] == "0", v["sessionsDisplay"])
    check("fr-FR grouping", v["attemptsDisplay"] == "1 234 567", repr(v["attemptsDisplay"]))
    v = dump(["--data=attempts=1320", "--data=locale=es-ES", "--advance=10"])
    check("es-ES does not group 4 digits", v["attemptsDisplay"] == "1320", v["attemptsDisplay"])
    lines = dump(["--data=currentScreen=2", "--advance=6"] + [f"--advance=6"] * 12, every=6)
    disp = [d for _, d in series(lines, "sessionsDisplay")]
    nums = [int(d) for d in disp[disp.index("0"):]] if "0" in disp else []
    check("hero counts up from 0 to the bound value (number layer is transparent until frame 12)",
          nums and nums == sorted(nums) and nums[-1] == 86, disp)
    v = dump(["--data=reducedMotion=true", "--data=currentScreen=2", "--advance=3"])
    check("reduced motion shows final value immediately", v["sessionsDisplay"] == "86", v["sessionsDisplay"])
    # 11. share flow pauses, dismissal restores previous pause state
    v = dump(["--data=currentScreen=10", "--advance=130", "--pointer=click@250,783", "--advance=5"])
    check("Share tap pauses and marks sharing", v["isPaused"] is True and v["isSharing"] is True, (v["isPaused"], v["isSharing"]))
    # 12. hold drag never navigates
    v = dump(["--advance=120", "--pointer=drag@115,605>230,480:10", "--advance=30"])
    check("dragging the hold does not navigate", v["currentScreen"] == 1, v["currentScreen"])

    responsive()

    os.makedirs(os.path.join(ROOT, "captures", "data"), exist_ok=True)
    with open(os.path.join(ROOT, "captures", "data", "verify-report.json"), "w") as f:
        json.dump(RESULTS, f, indent=1, ensure_ascii=False)
    print(f"\n{sum(r['pass'] for r in RESULTS)}/{len(RESULTS)} checks passed")


if __name__ == "__main__":
    main()
