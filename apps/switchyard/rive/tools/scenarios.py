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


def run(name, steps, fixture=None, data=()):
    png = os.path.join(OUT, f"{name}.png")
    dump = os.path.join(OUT, f"{name}.json")
    args = [f"--screenshot={png}", f"--data-dump={dump}"] + fixture_args(fixture) + [f"--data={d}" for d in data]
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
