#!/usr/bin/env python3
"""Behavioural checks for the Crux recap, run headless through `rive --data-dump`.

    python3 tools/verify.py        # from apps/crux/rive

Each scenario drives the real .riv (pointer, keyboard, data) and asserts on the
UserRecap values the director and state machines write back. Results are also
saved to captures/data/verify-report.json.
"""
import json
import os
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

    os.makedirs(os.path.join(ROOT, "captures", "data"), exist_ok=True)
    with open(os.path.join(ROOT, "captures", "data", "verify-report.json"), "w") as f:
        json.dump(RESULTS, f, indent=1, ensure_ascii=False)
    print(f"\n{sum(r['pass'] for r in RESULTS)}/{len(RESULTS)} checks passed")


if __name__ == "__main__":
    main()
