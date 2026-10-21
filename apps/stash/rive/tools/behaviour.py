#!/usr/bin/env python3
"""Headless behaviour checks for the Stash recap (run from the project dir).

Each scenario drives the real state machine + director through the CLI with
synthetic pointer / key / data input, samples UserRecap every frame, and
asserts on what changed. Results are written to captures/tests/behaviour.txt.

    python3 tools/behaviour.py
"""
import json
import os
import subprocess
import sys

RIVE = os.environ.get("RIVE", os.path.expanduser("~/.rive/bin/rive"))
OUT = "captures/tests"
os.makedirs(OUT, exist_ok=True)
FILTER = "currentScreen,_evt*,_heard*,_coinNudge,_finished,isPaused,_frozen,_holding,screenProgress,_visibleCount,_visibleIndex,_navDir,_focus,personaName,_personaSlot,totalSaved,deposits"


def run(name, args):
    path = f"{OUT}/{name}.jsonl"
    cmd = [RIVE, ".", "--quiet", f"--data-dump={path}", "--data-dump-every=1", f"--data-dump-filter={FILTER}"] + args
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rows = [json.loads(l) for l in open(path)]
    events, state = [], {}
    for r in rows[1:]:
        for v in r.get("values", []):
            if v.get("fired"):
                events.append((r["frame"], v["path"]))
            else:
                if state.get(v["path"]) != v.get("value"):
                    events.append((r["frame"], f'{v["path"]}={v.get("value")}'))
                state[v["path"]] = v.get("value")
    return events, state


def screens(events):
    return [e for f, e in events if e.startswith("currentScreen=")]


def count(events, name):
    return sum(1 for f, e in events if e == name)


results = []


def check(label, ok, detail=""):
    results.append(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


T = "--advance=2.4s"
# 1. tap right two-thirds advances, left third goes back
ev, st = run("tap_next_back", [T, "--pointer=click@300,450", "--advance=2.4s", "--pointer=click@60,450", "--advance=2.4s"])
check("right-side tap advances, left-side tap goes back", screens(ev)[-2:] == ["currentScreen=2", "currentScreen=1"], str(screens(ev)))
check("screenChanged fires once per change (initial + 2)", count(ev, "_evtScreenChanged") == 3, str(count(ev, "_evtScreenChanged")))

# 2. rapid taps settle on the final requested scene, one event per change
ev, st = run("rapid_taps", [T] + ["--pointer=click@300,450", "--pointer=move@300,460"] * 5 + ["--advance=3s"])
check("five rapid taps land on scene 6", st.get("currentScreen") == 6, str(screens(ev)))
check("one screenChanged per scene visited", count(ev, "_evtScreenChanged") == 1 + len(screens(ev)) - 1, f'{count(ev, "_evtScreenChanged")} events, {screens(ev)}')

# 3. hold pauses, release does not navigate
ev, st = run("hold", [T, "--pointer=down@300,450", "--advance=1.5s", "--pointer=up@300,450", "--advance=1s"])
held = any(e == "_holding=True" for f, e in ev) and any(e == "_frozen=True" for f, e in ev)
check("press-and-hold freezes (holding/frozen true while held)", held, str([e for f, e in ev if "_hold" in e or "_frozen" in e]))
check("releasing a hold does not navigate", st.get("currentScreen") == 1, str(screens(ev)))

# 4. pause button freezes dwell, play resumes from the same point
ev, st = run("pause", [T, "--advance=1s", "--pointer=click@346,32", "--advance=4s", "--data-dump-filter=screenProgress"])
ev2, st2 = run("pause_resume", [T, "--advance=1s", "--pointer=click@346,32", "--advance=3s", "--pointer=move@200,600",
                                "--pointer=click@346,32", "--advance=1s"])
check("pause button sets isPaused and holds progress", st.get("isPaused") is True and st.get("currentScreen") == 1,
      f'isPaused={st.get("isPaused")} progress={st.get("screenProgress")}')
check("play resumes (isPaused false again, still on scene 1 then advancing)", st2.get("isPaused") is False, str(st2.get("screenProgress")))

# 5. keyboard: Right / Left / Space
ev, st = run("keys", [T, "--key=right", "--advance=2.4s", "--key=right", "--advance=2.4s", "--key=left", "--advance=1s", "--key=space", "--advance=10"])
check("Right, Right, Left navigates 1->2->3->2", screens(ev)[-3:] == ["currentScreen=2", "currentScreen=3", "currentScreen=2"], str(screens(ev)))
check("Space toggles pause", st.get("isPaused") is True)

# 6. hidden scenes are skipped both ways and the progress adapts
hide = ["--data=showScreen3=false", "--data=showScreen5=false", "--data=showScreen6=false"]
ev, st = run("hidden", hide + [T] + ["--key=right", "--advance=2.4s"] * 3 + ["--key=left", "--advance=2.4s"])
check("hidden 3,5,6: forward 1->2->4->7, back to 4", screens(ev)[1:] == ["currentScreen=2", "currentScreen=4", "currentScreen=7", "currentScreen=4"], str(screens(ev)))
check("progress shows 7 segments", st.get("_visibleCount") == 7, str(st.get("_visibleCount")))

# 7. full auto-advance reaches the summary, recapFinished fires once, no loop
ev, st = run("autoplay", ["--data=autoAdvanceSeconds=3", "--advance=70s"])
check("auto-advance visits all ten scenes in order", screens(ev) == [f"currentScreen={k}" for k in range(1, 11)], str(screens(ev)))
check("recapFinished fires exactly once", count(ev, "_evtRecapFinished") == 1)
check("stays on the summary (no auto-loop)", st.get("currentScreen") == 10)

# 8. autoAdvanceEnabled=false never advances; unsafe durations clamp to 3 s
ev, st = run("auto_off", ["--data=autoAdvanceEnabled=false", "--advance=20s"])
check("auto-advance disabled stays on scene 1", st.get("currentScreen") == 1)
ev, st = run("clamp", ["--data=autoAdvanceSeconds=0.2", "--advance=4s"])
check("autoAdvanceSeconds=0.2 is clamped (no advance within 4 s)", st.get("currentScreen") == 1)

# 9. sharing / backgrounded never advance
ev, st = run("backgrounded", ["--data=appBackgrounded=true", "--data=autoAdvanceSeconds=3", "--advance=12s"])
check("appBackgrounded freezes the timer", st.get("currentScreen") == 1)

# 10. replay resets progress and the completion latch
ev, st = run("replay", ["--data=currentScreen=10", "--advance=3s", "--pointer=click@100,792", "--advance=3s"])
check("Replay returns to scene 1 and clears the latch", st.get("currentScreen") == 1 and st.get("_finished") is False,
      f'{screens(ev)} finished={st.get("_finished")}')

# 11. share button fires shareTapped
ev, st = run("share", ["--data=currentScreen=10", "--advance=3s", "--pointer=click@280,792", "--advance=10"])
check("Share fires shareTapped exactly once", count(ev, "_evtShareTapped") == 1)

# 12. continue / previous buttons
ev, st = run("buttons", [T, "--pointer=click@230,792", "--advance=2.4s", "--pointer=click@43,792", "--advance=1s"])
check("Continue then Previous buttons navigate 1->2->1", screens(ev)[-2:] == ["currentScreen=2", "currentScreen=1"], str(screens(ev)))

# 13. runtime data updates: persona index remaps name atomically, invalid index falls back to 0
ev, st = run("persona", ["--data=personaIndex=2", "--advance=10"])
check("personaIndex=2 -> Roundup Ranger", st.get("personaName") == "Roundup Ranger" and st.get("_personaSlot") == 2)
ev, st = run("persona_bad", ["--data=personaIndex=7", "--advance=10"])
check("personaIndex=7 falls back to row 0", st.get("_personaSlot") == 0 and st.get("personaName") == "Steady Builder")

# 14. sanitising: negative / non-integer counts
ev, st = run("sanitize", ["--data=totalSaved=-50", "--data=deposits=12.6", "--advance=5"])
check("negative money clamps to 0, counts round", st.get("totalSaved") == 0 and st.get("deposits") == 13,
      f'{st.get("totalSaved")} {st.get("deposits")}')

# 15. zero / new user: intro -> summary only
zero = ["--data=" + a for a in ["showScreen2=false", "showScreen3=false", "showScreen4=false", "showScreen5=false",
                                  "showScreen6=false", "showScreen7=false", "showScreen8=false", "showScreen9=false"]]
ev, st = run("zero_user", zero + [T, "--key=right", "--advance=2.4s"])
check("no eligible stats: intro -> summary, 2 segments", screens(ev)[-1] == "currentScreen=10" and st.get("_visibleCount") == 2,
      str(screens(ev)))

# 16. the signature tap toy (on the motif) nudges its coin and never navigates
ev, st = run("toy_tap", [T, "--pointer=click@307,662", "--advance=1s"])
check("tapping the motif's coin fires _coinNudge and does not navigate",
      count(ev, "_coinNudge") == 1 and st.get("currentScreen") == 1, f'{count(ev, "_coinNudge")} {screens(ev)}')

# 17. the real Rive events, heard by the EventProbe harness artboard (it nests the
#     Recap and listens to the events its state machine reports)
probe = ["--artboard=EventProbe"]
ev, st = run("events_autoplay", probe + ["--data=autoAdvanceSeconds=3", "--advance=70s"])
check("screenChanged heard as a Rive event once per scene (10)", count(ev, "_heardScreenChanged") == 10,
      str(count(ev, "_heardScreenChanged")))
check("recapFinished heard as a Rive event exactly once", count(ev, "_heardRecapFinished") == 1,
      str(count(ev, "_heardRecapFinished")))
ev, st = run("events_share", probe + ["--data=currentScreen=10", "--advance=3s", "--pointer=click@280,792", "--advance=10"])
check("shareTapped heard as a Rive event exactly once", count(ev, "_heardShareTapped") == 1,
      str(count(ev, "_heardShareTapped")))

open(f"{OUT}/behaviour.txt", "w").write("\n".join(results) + "\n")
print("\n".join(results))
sys.exit(0 if all(r.startswith("[PASS") for r in results) else 1)
