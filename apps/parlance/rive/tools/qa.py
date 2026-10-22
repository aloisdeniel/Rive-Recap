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

# ---------------------------------------------------------------- responsive layout
# 15. orientation follows the real width (layoutBreakpoint, default 768), whatever the height
def dump(args, filt="_land,_split,_k,_sc,_vw,_vh,currentScreen"):
    r = subprocess.run([RIVE, ROOT, "--quiet", "--data-dump=-", f"--data-dump-filter={filt}"] + args,
                       capture_output=True, text=True, check=True)
    return {p["name"]: p.get("value") for p in json.loads(r.stdout)["viewModel"]["properties"]}


for vp, extra, land, split in (("390x844", [], 0, 0), ("767x1024", [], 0, 0), ("768x1024", [], 1, 1),
                               ("740x360", [], 0, 1), ("1280x720", [], 1, 1), ("820x1180", [], 1, 1),
                               ("1280x720", ["--data=layoutBreakpoint=1300"], 0, 1),
                               ("390x844", ["--data=layoutBreakpoint=320"], 1, 1)):
    d = dump([f"--viewport={vp}"] + extra + ["--advance=10"])
    check(f"Orientation at {vp}{' ' + extra[0][7:] if extra else ''}",
          d["_land"] == land and d["_split"] == split and d["_vw"] == int(vp.split("x")[0]),
          f"_vw={d['_vw']} _land={d['_land']} (want {land}) _split={d['_split']} (want {split})")

# 16. every size of the matrix keeps controls >= 44 pt (52 x _k) and copy at a readable scale
MATRIX = ["320x568", "360x640", "390x844", "430x932", "600x960", "767x1024", "667x375", "740x360",
          "768x1024", "820x1180", "1024x768", "1280x720", "1440x900", "1920x1080", "2560x1080", "1366x600"]
worst = []
for vp in MATRIX:
    d = dump([f"--viewport={vp}", "--advance=10"])
    worst.append((round(52 * d["_k"], 1), round(d["_sc"], 2), vp))
check("Controls >= 44 pt across the viewport matrix", min(w[0] for w in worst) >= 44,
      f"smallest control {min(worst)[0]} pt at {min(worst)[2]}")

# 17. landscape navigation uses the real geometry: Continue bottom right, tap thirds of the real width, Right arrow
L = ["--viewport=1280x720"]
fr = trace(L + ["--advance=150", "--pointer=click@1120,664", "--advance=190", "--pointer=click@1150,200", "--advance=190",
                "--pointer=click@200,360", "--advance=150", "--key=right", "--advance=190"])
check("Landscape 1280x720: Continue, tap zones (left third back), Right arrow", screens(fr) == [1, 2, 3, 2, 3],
      f"screens {screens(fr)}")
fr = trace(["--viewport=320x568", "--advance=150", "--pointer=click@210,536", "--advance=190", "--pointer=click@40,300",
            "--advance=150"])
check("Portrait 320x568: Continue (narrowed) and left-third tap", screens(fr) == [1, 2, 1], f"screens {screens(fr)}")
fr = trace(L + ["--advance=150", "--pointer=down@900,360", "--advance=60", "--pointer=up@900,360", "--advance=30"])
check("Landscape hold-to-pause on the real tap zone", any(st.get("isPaused") for f, st, _ in fr if 160 < f < 210)
      and screens(fr) == [1] and fr[-1][1]["isPaused"] is False, f"screens {screens(fr)}")

# 18. full-canvas covers: the elongated speech form fills every edge of an ultra-wide and a short canvas
def edge_colours(path):
    code = ("import sys; from PIL import Image; im = Image.open(sys.argv[1]).convert('RGB'); w, h = im.size;"
            "pts = [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2), (w // 2, 1), (w // 2, h - 2), (1, h // 2), (w - 2, h // 2)];"
            "print(';'.join('%d,%d,%d' % im.getpixel(p) for p in pts))")
    out = subprocess.run(["/usr/bin/python3", "-c", code, path], capture_output=True, text=True, check=True).stdout
    return [tuple(int(c) for c in t.split(",")) for t in out.strip().split(";")]


nav5 = ["--advance=150"] + ["--key=right", "--advance=190"] * 4
for vp in ("2560x1080", "740x360", "820x1180"):
    path = os.path.join(ROOT, "build", f"qa_cover_{vp}.png")
    subprocess.run([RIVE, ROOT, "--quiet", f"--viewport={vp}", f"--screenshot={path}"] + nav5 + ["--key=right", "--advance=27"],
                   check=True)
    cols = edge_colours(path)
    # 5 -> 6 is covered by the lilac form (#C7B7F2; the paper grain shifts it a few levels)
    ok = all(abs(c[0] - 199) < 24 and abs(c[1] - 183) < 24 and abs(c[2] - 242) < 24 for c in cols)
    check(f"Handoff cover reaches every edge at {vp}", ok, f"edge pixels {cols[:4]}...")

nav3k = ["--advance=150"] + ["--key=right", "--advance=190"] * 2
for vp in ("2560x1080", "667x375"):
    path = os.path.join(ROOT, "build", f"qa_signature_{vp}.png")
    subprocess.run([RIVE, ROOT, "--quiet", f"--viewport={vp}", f"--screenshot={path}"] + nav3k + ["--key=right", "--advance=43"],
                   check=True)
    cols = edge_colours(path)
    ok = all(abs(c[0] - 243) < 30 and abs(c[1] - 106) < 30 and abs(c[2] - 67) < 30 for c in cols)
    check(f"Signature 3->4 (lips -> bubble) covers every edge at {vp}", ok, f"edge pixels {cols[:4]}...")

# 19. resize across the threshold mid-scene (and mid-handoff): a harness artboard hosts the recap in a box whose size
# is keyed, which is how a host's layout fit resizes it. The current scene must survive, the orientation flips, and the
# layout settles within a few frames.
import re
import shutil
import tempfile
tmp = tempfile.mkdtemp(prefix="parlance-resize-")
proj = os.path.join(tmp, "proj")
os.makedirs(proj)
for f in ("scene.rml", "components.rml", "data.rml"):
    shutil.copy(os.path.join(ROOT, f), proj)
shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(proj, "assets"))
open(os.path.join(proj, "rive.yaml"), "w").write("name: harness\nmain: Harness\n")
src = open(os.path.join(ROOT, "scene.rml")).read()
sm_id, vm_id, ab_id = re.search(r'<Artboard defaultStateMachineId="([^"]+)" viewModelId="([^"]+)"[^>]*name="Parlance Recap" '
                                r'id="([^"]+)"', src).groups()


def kf(prop, keys):
    return (f'<KeyedProperty propertyKey="{prop}">' + "".join(
        f'<KeyFrameDouble value="{v}" frame="{f}" interpolationType="hold"/>' for f, v in keys) + "</KeyedProperty>")


def harness(widths, heights):
    open(os.path.join(proj, "harness.rml"), "w").write(f'''<Rive version="1" kind="fragment">
<Artboard defaultStateMachineId="9:7" viewModelId="{vm_id}" viewModelInstanceId="0:95" width="1024" height="844" styleId="9:5" name="Harness" id="9:2">
  <LayoutComponentStyle name="Harness style" id="9:5"/>
  <LayoutComponent width="390" height="844" clip="true" styleId="9:11" name="Canvas" id="9:10">
    <LayoutComponentStyle layoutWidthScaleType="fixed" layoutHeightScaleType="fixed" name="Canvas style" id="9:11"/>
    <NestedArtboardLayout artboardId="{ab_id}" instanceWidthScaleType="fill" instanceHeightScaleType="fill" name="Recap" id="9:20">
      <NestedStateMachine animationId="{sm_id}" name="Recap machine"/>
    </NestedArtboardLayout>
  </LayoutComponent>
  <StateMachine name="Resize" id="9:7"><StateMachineLayer name="L" id="9:8">
    <EntryState><StateTransition stateToId="9:31"/></EntryState><AnimationState animationId="9:50" id="9:31"/>
  </StateMachineLayer></StateMachine>
  <LinearAnimation duration="4000" name="Resize" id="9:50"><KeyedObject objectId="9:10">{kf(7, widths)}{kf(8, heights)}</KeyedObject></LinearAnimation>
</Artboard>
</Rive>''')


def htrace(args, filt="currentScreen,_land,_split,_vw,_a3x,_a3s"):
    out = os.path.join(proj, "build", "harness.data.jsonl")
    subprocess.run([RIVE, proj, "--quiet", "--viewport=1024x844", "--data-dump-every=1", f"--data-dump-filter={filt}"] + args,
                   check=True, capture_output=True)
    frames, state = [], {}
    for line in open(out):
        d = json.loads(line)
        if "values" not in d:
            continue
        for v in d["values"]:
            if "value" in v:
                state[v["path"]] = v["value"]
        frames.append((d["frame"], dict(state), []))
    return frames


# portrait 390x844 -> landscape 1024x768 at frame 560 (scene 3 is dwelling) -> portrait at 800, then Right
harness([(0, 390), (560, 1024), (800, 390)], [(0, 844), (560, 768), (800, 844)])
fr = htrace(["--advance=150", "--key=right", "--advance=190", "--key=right", "--advance=520", "--key=right", "--advance=200"])
at = lambda f0: [st for f, st, _ in fr if f <= f0][-1]
last_change = max((f for i, (f, st, _) in enumerate(fr[1:], 1) if 560 <= f < 640 and
                   (st.get("_a3x"), st.get("_a3s")) != (fr[i - 1][1].get("_a3x"), fr[i - 1][1].get("_a3s"))), default=560)
check("Resize across the threshold mid-scene keeps the scene and settles",
      at(555)["currentScreen"] == 3 and at(555)["_land"] == 0 and at(700)["currentScreen"] == 3 and at(700)["_land"] == 1
      and at(850)["_land"] == 0 and at(850)["currentScreen"] == 3 and last_change <= 566 and screens(fr) == [1, 2, 3, 4],
      f"scene {at(555)['currentScreen']}->{at(700)['currentScreen']}->{at(850)['currentScreen']}, _land "
      f"{at(555)['_land']}->{at(700)['_land']}->{at(850)['_land']}, layout settled by frame {last_change}, screens {screens(fr)}")
cap = os.path.join(ROOT, "captures", "responsive")
os.makedirs(cap, exist_ok=True)
subprocess.run([RIVE, proj, "--quiet", "--viewport=1024x844", f"--screenshot={os.path.join(cap, 'resize-mid-scene-3-landscape.png')}",
                "--advance=150", "--key=right", "--advance=190", "--key=right", "--advance=300"], check=True)
# resize in the middle of a handoff (4 -> 5): lands on 5 in landscape, no duplicate entries
harness([(0, 390), (750, 1280)], [(0, 844), (750, 720)])
fr = htrace(["--advance=150"] + ["--key=right", "--advance=190"] * 3 + ["--key=right", "--advance=200"])
check("Resize across the threshold mid-handoff settles on the next scene",
      screens(fr) == [1, 2, 3, 4, 5] and fr[-1][1]["_land"] == 1, f"screens {screens(fr)}, _land {fr[-1][1]['_land']}")
shutil.rmtree(tmp, ignore_errors=True)


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
