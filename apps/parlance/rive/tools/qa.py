#!/usr/bin/env python3
"""Headless behaviour checks for the Parlance recap. Writes captures/qa-report.txt.

Each scenario drives the real state machine through the rive CLI (pointer, keys,
--data) and reads the UserRecap view model back with --data-dump-every.
Plain Rive events are not reported by the headless CLI, so event checks use the
state the firing states write (currentScreen for screenChanged, _finishedLatch
for recapFinished) plus a byte check that the events exist in the built .riv.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RIVE = os.path.expanduser("~/.rive/bin/rive")
OUT = os.path.join(ROOT, "build", "parlance-recap.data.jsonl")
CONT = "--pointer=click@260,790"
PREV = "--pointer=click@50,790"
PAUSE = "--pointer=click@112,790"
RIGHT_REGION = "--pointer=click@300,250"
LEFT_REGION = "--pointer=click@60,250"
results = []


def trace(args, filt="currentScreen,isPaused,_finishedLatch,screenProgress,goNext,goPrevious,personaName,personaColor"):
    cmd = [RIVE, ROOT, "--quiet", "--data-dump-every=1", f"--data-dump-filter={filt}"] + args
    subprocess.run(cmd, check=True)
    frames = []
    state = {}
    for line in open(OUT):
        d = json.loads(line)
        if "values" not in d:
            continue
        fired = []
        for v in d["values"]:
            if v.get("fired"):
                fired.append(v["path"])
            elif "value" in v:
                state[v["path"]] = v["value"]
        frames.append((d["frame"], dict(state), fired))
    return frames


def screens(frames):
    out = []
    for f, st, _ in frames:
        s = st.get("currentScreen")
        if not out or out[-1] != s:
            out.append(s)
    return out


def check(name, ok, detail):
    results.append(("PASS" if ok else "FAIL", name, detail))


# 1. next / back with the visible buttons
fr = trace(["--advance=150", CONT, "--advance=190", CONT, "--advance=190", PREV, "--advance=150"])
check("Continue/Previous buttons", screens(fr) == [1, 2, 3, 2], f"screens {screens(fr)}")

# 2. tap regions: right two-thirds advances, left third goes back
fr = trace(["--advance=150", RIGHT_REGION, "--advance=190", RIGHT_REGION, "--advance=190", LEFT_REGION, "--advance=120"])
check("Tap regions (right=next, left=back)", screens(fr) == [1, 2, 3, 2], f"screens {screens(fr)}")

# 3. rapid taps settle on the last requested scene without skipping events
taps = []
for _ in range(5):
    taps += [CONT, "--advance=4"]
fr = trace(["--advance=150"] + taps + ["--advance=400"])
sc = screens(fr)
final = fr[-1][1]["currentScreen"]
check("Rapid taps (5 taps in ~0.4s) settle on scene 6", final == 6 and len(sc) == len(set(sc)) and sc == sorted(sc),
      f"screens entered {sc} (a tap during an exit skips the scene being handed to); final scene {final}")

# 4. hold pauses, release resumes and does not navigate
fr = trace(["--advance=150", "--pointer=down@300,400", "--advance=60", "--pointer=up@300,400", "--advance=30"])
paused_during = any(st.get("isPaused") for f, st, _ in fr if 160 < f < 210)
check("Hold to pause / release resumes without a tap", paused_during and screens(fr) == [1] and fr[-1][1]["isPaused"] is False,
      f"paused while held={paused_during}, screens {screens(fr)}, paused after release={fr[-1][1]['isPaused']}")

# 5. pause button freezes the dwell timer and preserves progress; play resumes
fr = trace(["--advance=200", PAUSE, "--advance=300", PAUSE, "--advance=60"])
prog_at = {f: st.get("screenProgress") for f, st, _ in fr}
p1 = prog_at.get(max(k for k in prog_at if k <= 260))
p2 = prog_at.get(max(k for k in prog_at if k <= 500))
p3 = fr[-1][1]["screenProgress"]
check("Pause freezes dwell progress; play resumes from same point",
      abs(p1 - p2) < 1e-6 and p3 > p2 and screens(fr) == [1], f"progress paused {p1:.3f} -> {p2:.3f}, resumed to {p3:.3f}")

# 6. keyboard: Right/Left navigate, Space toggles pause (focus is set by the file on boot)
fr = trace(["--advance=150", "--key=right", "--advance=190", "--key=right", "--advance=190", "--key=left", "--advance=150",
            "--key=space", "--advance=10"])
check("Keyboard Right/Left/Space", screens(fr)[:4] == [1, 2, 3, 2] and fr[-1][1]["isPaused"] is True,
      f"screens {screens(fr)}, paused={fr[-1][1]['isPaused']}")
fr = trace(["--advance=150", "--key=tab", "--key=tab", "--key=enter", "--advance=200"],
           filt="currentScreen,_focusIndex,isPaused")
check("Keyboard Tab moves focus, Enter activates focused control",
      fr[-1][1].get('_focusIndex') == 2 and fr[-1][1].get('isPaused') is True, f"focus index after 2x Tab = {fr[-1][1].get('_focusIndex')}, screens {screens(fr)}, paused={fr[-1][1].get('isPaused')}")

# 7. hidden scenes are skipped in both directions
fr = trace(["--data=showScreen3=false", "--data=showScreen4=false", "--advance=150", CONT, "--advance=190", CONT,
            "--advance=190", PREV, "--advance=190"])
check("Hidden scenes skipped forward and back", screens(fr) == [1, 2, 5, 2], f"screens {screens(fr)}")

# 8. no eligible stats -> intro then welcoming summary
args = [f"--data=showScreen{k}=false" for k in range(2, 10)]
fr = trace(args + ["--advance=150", CONT, "--advance=250"])
check("New user: intro -> summary", screens(fr) == [1, 10], f"screens {screens(fr)}")

# 9. full auto-advance reaches the summary once, latches recapFinished, never loops
fr = trace(["--data=autoAdvanceSeconds=4", "--advance=75s"])
latch_changes = [f for i, (f, st, _) in enumerate(fr[1:], 1) if st.get("_finishedLatch") != fr[i - 1][1].get("_finishedLatch")]
check("Auto-advance 1..10, recapFinished once, no loop", screens(fr) == list(range(1, 11)) and len(latch_changes) == 1,
      f"screens {screens(fr)}, latch set at frames {latch_changes}")

# 10. autoAdvanceEnabled=false holds the scene
fr = trace(["--data=autoAdvanceEnabled=false", "--advance=20s"])
check("autoAdvanceEnabled=false never advances", screens(fr) == [1], f"screens {screens(fr)}")

# 11. unsafe dwell is clamped (1 s requested -> 4 s minimum)
fr = trace(["--data=autoAdvanceSeconds=1", "--advance=8s"])
first_change = next((f for f, st, _ in fr if st.get("currentScreen") == 2), None)
check("Dwell clamped to >= 4 s", first_change is not None and first_change > 130 + 4 * 60 - 5,
      f"scene 2 entered at frame {first_change} (entrance 130f + clamped dwell 240f)")

# 12. replay resets progress and the completion latch
fr = trace(["--data=autoAdvanceSeconds=4", "--advance=70s", "--pointer=click@158,790", "--advance=120"])
check("Replay returns to scene 1 and clears latch", fr[-1][1]["currentScreen"] == 1 and fr[-1][1]["_finishedLatch"] is False,
      f"final screen {fr[-1][1]['currentScreen']}, latch {fr[-1][1]['_finishedLatch']}")

# 13. persona mapping is atomic and unknown indices fall back to row 0
for idx, name in ((0, "Conversation Starter"), (1, "Phrase Collector"), (2, "Careful Listener"), (3, "Brave Improviser"),
                  (9, "Conversation Starter"), (-2, "Conversation Starter")):
    fr = trace([f"--data=personaIndex={idx}", "--advance=10"])
    st = fr[-1][1]
    check(f"personaIndex={idx} -> name/colour", st.get("personaName") == name,
          f"personaName={st.get('personaName')!r} personaColor={st.get('personaColor')}")

# 13b. signature interaction: tapping the mouth plays the elastic expression and never navigates
nav3 = ["--advance=150", CONT, "--advance=190", CONT, "--advance=190"]
fr = trace(nav3 + ["--pointer=click@195,486", "--advance=120"])
check("Mouth tap (scene 3) does not trigger navigation", fr[-1][1]["currentScreen"] == 3, f"screens {screens(fr)}")
import hashlib
def shot(extra, name):
    path = os.path.join(ROOT, "build", name)
    subprocess.run([RIVE, ROOT, "--quiet", f"--screenshot={path}"] + extra, check=True)
    return hashlib.md5(open(path, "rb").read()).hexdigest()
h_rest = shot(nav3 + ["--advance=8"], "qa_mouth_rest.png")
h_tap = shot(nav3 + ["--pointer=click@195,486", "--advance=6"], "qa_mouth_tap.png")
check("Mouth tap changes the picture (elastic squash)", h_rest != h_tap, f"rest {h_rest[:8]} vs tapped {h_tap[:8]}")

# 13c. runtime data reaches the visible numbers (same scene, different bound value)
h_a = shot(["--advance=150", CONT, "--advance=190"], "qa_data_a.png")
h_b = shot(["--data=conversations=98765", "--advance=150", CONT, "--advance=190"], "qa_data_b.png")
check("Bound hero number follows UserRecap.conversations", h_a != h_b, f"204 render {h_a[:8]} vs 98,765 render {h_b[:8]}")

# 14. events exist in the built file
riv = open(os.path.join(ROOT, "build", "parlance-recap.riv"), "rb").read()
for ev in ("screenChanged", "shareTapped", "recapFinished", "mouthTapped"):
    check(f"event '{ev}' exported", ev.encode() in riv, "found in .riv bytes" if ev.encode() in riv else "missing")

with open(os.path.join(ROOT, "captures", "qa-report.txt"), "w") as f:
    for r in results:
        f.write(f"{r[0]}  {r[1]}: {r[2]}\n")
for r in results:
    print(f"{r[0]}  {r[1]}: {r[2]}")
sys.exit(0 if all(r[0] == "PASS" for r in results) else 1)
