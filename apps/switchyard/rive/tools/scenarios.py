#!/usr/bin/env python3
"""Headless interaction scenarios for the Switchyard recap.

Builds the scene with SWITCHYARD_DEBUG_EVENTS=1 (host events become
OpenUrlEvents so the CLI logs `url event://<name>` whenever one fires), runs
each scenario through `rive --screenshot --data-dump`, asserts on the logged
events and the dumped UserRecap values, then restores the normal build.

Run from apps/switchyard/rive:  python3 tools/scenarios.py
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import PROJECT, adv, click, rive, fixture_args  # noqa: E402

OUT = os.path.join(PROJECT, "captures", "scenarios")
os.makedirs(OUT, exist_ok=True)
NEXT, PREV, PAUSE = (259, 790), (50, 790), (114, 790)
SHARE, REPLAY = (207, 790), (318, 790)
STORY_R, STORY_L = (300, 420), (60, 420)


def gen(debug):
    env = dict(os.environ, SWITCHYARD_DEBUG_EVENTS="1" if debug else "0")
    subprocess.run([sys.executable, os.path.join(PROJECT, "tools", "gen.py")], env=env, check=True,
                   capture_output=True)


def run(name, steps, fixture=None, data=(), size=None, resize=None):
    """size=(w, h): the artboard size (the debug build binds it to _testW/_testH, as a
    host's layout fit would set it). resize=(t, w, h): resize to w x h at t seconds."""
    png = os.path.join(OUT, f"{name}.png")
    dump = os.path.join(OUT, f"{name}.json")
    args = [f"--screenshot={png}", f"--data-dump={dump}"] + fixture_args(fixture) + [f"--data={d}" for d in data]
    if size or resize:
        w, h = size or (390, 844)
        args += [f"--data=_testW={w}", f"--data=_testH={h}"]
        vw, vh = w, h
        if resize:
            t, w2, h2 = resize
            args += [f"--data=_testAt={t}", f"--data=_testW2={w2}", f"--data=_testH2={h2}"]
            vw, vh = max(w, w2), max(h, h2)
        args.append(f"--viewport={vw}x{vh}")
    args += steps
    code, log = rive(args)
    if code:
        raise SystemExit(log)
    events = re.findall(r"url event://(\w+)", log)
    vm = {p["name"]: p.get("value") for p in json.load(open(dump))["viewModel"]["properties"]}
    return events, vm


RESULTS = []


def check(name, cond, detail):
    RESULTS.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + " :: " + detail)


def real(vm, key, x, y):
    """design point of a placed group -> real artboard point"""
    return (round(vm[f"_{key}X"] + x * vm[f"_{key}S"]), round(vm[f"_{key}Y"] + y * vm[f"_{key}S"]))


def dock_points(vm):
    """real centres of Prev and Continue from the dumped chrome layout"""
    cs, dy = vm["_cs"], vm["_dockY"]
    y = round(dy + (790 + vm["_dockBtnY"]) * cs)
    return (round((vm["_dockL"] + 50) * cs), y), (round((vm["_dockR"] + 259) * cs), y)


def orientation_checks():
    """Responsive: breakpoint rule, real-size interaction, resizes across the threshold."""
    # 14. the breakpoint is a pure width rule, tunable through layoutBreakpoint
    got = {}
    for w, h in ((767, 1024), (768, 1024), (667, 375), (1280, 720), (820, 1180)):
        _, vm = run(f"14_breakpoint_{w}x{h}", adv(20), size=(w, h))
        got[(w, h)] = vm["_landscape"]
    _, vm_bp = run("14_breakpoint_override", adv(20), size=(1280, 720), data=["layoutBreakpoint=1300"])
    check("breakpoint rule", got[(767, 1024)] == 0 and got[(768, 1024)] == 1 and got[(667, 375)] == 0
          and got[(1280, 720)] == 1 and got[(820, 1180)] == 1 and vm_bp["_landscape"] == 0,
          f"767x1024={got[(767, 1024)]} 768x1024={got[(768, 1024)]} 667x375={got[(667, 375)]} "
          f"1280x720={got[(1280, 720)]} 820x1180={got[(820, 1180)]} 1280 with breakpoint 1300={vm_bp['_landscape']}")

    # 15. landscape interaction at the real size: tap zones use the real width (left
    # third back, right two-thirds next), hold pauses, Right arrow advances, the dock
    # buttons and the route chips are hit where they are drawn
    size = (1280, 720)
    _, vm0 = run("15_landscape_layout", adv(20), size=size)
    prev_pt, next_pt = dock_points(vm0)
    steps = adv(40) + click(1000, 360) + adv(30) + click(500, 360) + adv(30) + ["--key=right"] + adv(30) + \
        ["--key=right"] + adv(30) + click(*prev_pt) + adv(30) + click(*next_pt) + adv(30) + click(300, 360) + adv(30)
    ev, vm = run("15a_landscape_taps", steps, size=size)
    # 1 -(tap x=1000)-> 2 -(tap x=500, middle third)-> 3 -(Right)-> 4 -(Right)-> 5 -(Prev)-> 4 -(Continue)-> 5
    # -(tap x=300, left third)-> 4
    check("landscape taps / keys / dock", vm["currentScreen"] == 4 and ev.count("screenChanged") == 8,
          f"screen={vm['currentScreen']} (expect 4) screenChanged x{ev.count('screenChanged')} (expect 8)")
    steps = adv(60) + [f"--pointer=move@1000,360", "--pointer=down@1000,360"] + adv(60)
    _, vm_h = run("15b_landscape_hold", steps, size=size)
    _, vm_r = run("15c_landscape_release", steps + ["--pointer=up@1000,360"] + adv(10), size=size)
    check("landscape hold-to-pause", vm_h["isPaused"] is True and vm_r["isPaused"] is False
          and vm_r["currentScreen"] == 1, f"held={vm_h['isPaused']} released={vm_r['isPaused']} "
          f"screen={vm_r['currentScreen']}")
    _, v4 = run("15d_landscape_chip_layout", adv(20), size=size, data=["currentScreen=4"])
    chip = real(v4, "s4art", 146, 488)       # B12
    ev, vm = run("15e_landscape_chip", adv(30) + click(*chip) + adv(60), size=size, data=["currentScreen=4"])
    check("landscape route chip isolated", vm["currentScreen"] == 4 and vm["_activeRoute"] == 2,
          f"chip at {chip}: screen={vm['currentScreen']} activeRoute={vm['_activeRoute']}")

    # 16. resize across the threshold mid-scene: the scene is kept, nothing re-fires,
    # the new layout settles and the story carries on
    steps = adv(30) + ["--key=right"] + adv(30) + ["--key=right"] + adv(60) + adv("2s")
    ev, vm = run("16a_resize_portrait_to_landscape", steps, resize=(2.0, 1280, 720), size=(390, 844))
    progress_a = vm["screenProgress"]
    ev2, vm2 = run("16b_resize_then_next", steps + ["--key=right"] + adv(150), resize=(2.0, 1280, 720),
                   size=(390, 844))
    check("resize portrait -> landscape mid-scene", vm["currentScreen"] == 3 and vm["_landscape"] == 1
          and ev.count("screenChanged") == 3 and vm["_vw"] == 1280 and progress_a > 0
          and vm2["currentScreen"] == 4 and ev2.count("screenChanged") == 4,
          f"screen={vm['currentScreen']} landscape={vm['_landscape']} vw={vm['_vw']} "
          f"screenChanged x{ev.count('screenChanged')} progress={progress_a:.3f}; then Right -> {vm2['currentScreen']}")
    # landscape -> portrait while the 4 -> 5 roundel is mid-flight, then settle
    steps = adv(40) + ["--key=right"] * 3 + adv(150) + ["--key=right"] + adv(20) + adv(150)
    ev, vm = run("16c_resize_mid_transition", steps, resize=(3.2, 600, 960), size=(1280, 720),
                 data=["autoAdvanceEnabled=false"])
    check("resize landscape -> portrait mid-transition", vm["currentScreen"] == 5 and vm["_landscape"] == 0
          and ev.count("screenChanged") == 5 and vm["_vw"] == 600,
          f"screen={vm['currentScreen']} landscape={vm['_landscape']} vw={vm['_vw']} "
          f"screenChanged x{ev.count('screenChanged')}")
    # the persona and summary through a resize, then back on the original size
    steps = adv(60) + adv(200)
    ev, vm = run("16d_resize_summary", steps, resize=(1.0, 740, 360), size=(1440, 900),
                 data=["currentScreen=10"])
    check("resize on the summary keeps it settled", vm["currentScreen"] == 10 and ev.count("recapFinished") == 1
          and vm["_landscape"] == 0, f"screen={vm['currentScreen']} recapFinished x{ev.count('recapFinished')} "
          f"landscape={vm['_landscape']}")


def main():
    gen(True)
    try:
        # 1. next/back via story taps and buttons; events exactly once per change
        steps = adv(60) + click(*STORY_R) + adv(30) + click(*NEXT) + adv(30) + click(*STORY_L) + adv(30) + \
            click(*PREV) + adv(30)
        ev, vm = run("01_next_back", steps)
        check("next/back", vm["currentScreen"] == 1 and ev.count("screenChanged") == 5,
              f"screen={vm['currentScreen']} screenChanged x{ev.count('screenChanged')} (expect 5: 1,2,3,2,1)")

        # 2. rapid taps settle on the final requested scene
        steps = adv(30)
        for _ in range(5):
            steps += click(*STORY_R) + adv(2)
        steps += adv(140)
        ev, vm = run("02_rapid_taps", steps)
        check("rapid taps", vm["currentScreen"] == 6 and ev.count("screenChanged") == 6,
              f"screen={vm['currentScreen']} events={ev.count('screenChanged')}")

        # 3. hold pauses, release does not navigate and restores play
        steps = adv(60) + ["--pointer=move@300,420", "--pointer=down@300,420"] + adv(60)
        ev_h, vm_h = run("03a_hold_down", steps)
        steps2 = steps + ["--pointer=up@300,420"] + adv(10)
        ev, vm = run("03b_hold_release", steps2)
        check("hold to pause", vm_h["isPaused"] is True and vm["isPaused"] is False and vm["currentScreen"] == 1,
              f"held paused={vm_h['isPaused']} released paused={vm['isPaused']} screen={vm['currentScreen']}")

        # 4. pause button freezes the dwell timer; play resumes from same point
        steps = adv(200) + click(*PAUSE) + adv(10)
        _, vm_a = run("04a_paused", steps)
        _, vm_b = run("04b_paused_later", steps + adv(240))
        _, vm_c = run("04c_resumed", steps + adv(240) + click(*PAUSE) + adv(30))
        check("pause/resume", vm_a["isPaused"] and abs(vm_a["screenProgress"] - vm_b["screenProgress"]) < 1e-6
              and vm_c["screenProgress"] > vm_b["screenProgress"] and not vm_c["isPaused"],
              f"progress paused {vm_a['screenProgress']:.3f} -> {vm_b['screenProgress']:.3f}, resumed "
              f"{vm_c['screenProgress']:.3f}")

        # 5. keyboard: Right, Right, Left, Space
        steps = adv(30) + ["--key=right"] + adv(20) + ["--key=right"] + adv(20) + ["--key=left"] + adv(20) + \
            ["--key=space"] + adv(10)
        ev, vm = run("05_keyboard", steps)
        check("keyboard", vm["currentScreen"] == 2 and vm["isPaused"] is True,
              f"screen={vm['currentScreen']} paused={vm['isPaused']}")

        # 6. hidden scenes are skipped both ways; progress adapts
        data = ["showScreen3=false", "showScreen4=false", "showScreen7=false"]
        steps = adv(30) + click(*NEXT) + adv(20) + click(*NEXT) + adv(20)
        ev, vm = run("06_hidden_forward", steps, data=data)
        steps_b = steps + click(*PREV) + adv(20)
        ev2, vm2 = run("06_hidden_back", steps_b, data=data)
        check("hidden scenes", vm["currentScreen"] == 5 and vm2["currentScreen"] == 2,
              f"1->next->next = {vm['currentScreen']} (expect 5); back = {vm2['currentScreen']} (expect 2)")

        # 7. full auto-advance reaches the summary, recapFinished exactly once, no auto-loop
        ev, vm = run("07_auto_advance", adv("80s"), data=["autoAdvanceSeconds=4"])
        check("auto-advance", vm["currentScreen"] == 10 and ev.count("recapFinished") == 1
              and ev.count("screenChanged") == 10,
              f"screen={vm['currentScreen']} screenChanged x{ev.count('screenChanged')} "
              f"recapFinished x{ev.count('recapFinished')}")

        # 8. summary: share event, back/forward does not re-fire finish, replay resets the latch
        steps = adv(30) + click(*STORY_R) + adv(150) + click(*SHARE) + adv(10) + click(*PREV) + adv(40) + \
            click(*NEXT) + adv(150) + click(*REPLAY) + adv(30)
        ev, vm = run("08_share_replay", steps, data=["currentScreen=9"])
        steps2 = steps + adv("60s")
        ev2, vm2 = run("08b_replay_to_end", steps2, data=["currentScreen=9", "autoAdvanceSeconds=4"])
        check("share + replay", ev.count("shareTapped") == 1 and ev.count("recapFinished") == 1
              and vm["currentScreen"] == 1 and ev2.count("recapFinished") == 2,
              f"shareTapped x{ev.count('shareTapped')}, finish before replay x{ev.count('recapFinished')}, "
              f"after replay+rerun x{ev2.count('recapFinished')}, screen after replay={vm['currentScreen']}")

        # 9. auto-advance disabled
        ev, vm = run("09_auto_off", adv("20s"), data=["autoAdvanceEnabled=false"])
        check("autoAdvanceEnabled=false", vm["currentScreen"] == 1, f"screen={vm['currentScreen']}")

        # 10. zero/new user: intro -> welcoming summary, no persona
        steps = adv(30) + click(*NEXT) + adv(150)
        ev, vm = run("10_zero_user", steps, fixture="zero-new-user.json")
        check("zero user", vm["currentScreen"] == 10 and vm["_isEmpty"] is True,
              f"intro -> {vm['currentScreen']} empty={vm['_isEmpty']}")

        # 11. runtime data update: change personaIndex mid-run -> atomic remap
        steps = adv(200)
        ev, vm = run("11_persona_runtime", steps, data=["currentScreen=9", "personaIndex=7"])
        check("unknown persona index falls back to row 0", vm["_personaSlot"] == 0
              and vm["personaName"] == "City Connector", f"slot={vm['_personaSlot']} name={vm['personaName']}")

        # 12. route chip does not navigate
        steps = adv(30) + click(62, 488) + adv(60)
        ev, vm = run("12_route_chip", steps, data=["currentScreen=4"])
        check("route chip isolated", vm["currentScreen"] == 4 and vm["_activeRoute"] == 1,
              f"screen={vm['currentScreen']} activeRoute={vm['_activeRoute']}")

        # 13. reduced motion: still navigates, counts are immediate
        steps = adv(30) + click(*NEXT) + adv(3)
        ev, vm = run("13_reduced_motion", steps, data=["reducedMotion=true"])
        check("reduced motion", vm["currentScreen"] == 2 and vm["_count2"] == 1,
              f"screen={vm['currentScreen']} count playhead={vm['_count2']}")
        orientation_checks()
    finally:
        gen(False)
    fails = [r for r in RESULTS if not r[1]]
    with open(os.path.join(OUT, "results.txt"), "w") as f:
        for n, ok, d in RESULTS:
            f.write(("PASS " if ok else "FAIL ") + n + " :: " + d + "\n")
    print(f"{len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
