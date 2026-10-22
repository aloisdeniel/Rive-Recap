#!/usr/bin/env bash
# Headless checks for the responsive layout: orientation per size, the tunable breakpoint,
# tap zones / hold / keys on a landscape canvas, the landscape persona glide, and a resize
# across the breakpoint mid-scene and mid-transition (through tools/resize_harness.py).
# Prints the view-model values each scenario ends on. Run from anywhere.
set -u
cd "$(dirname "$0")/.."
R="${RIVE:-$HOME/.rive/bin/rive}"
KEYS='currentScreen,_navDir,_screenChangedCount,_landscape,_stack,_artScale,_artX,_copyS,_bigK,_cardScale,_chromeS'
show() { python3 -c '
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw[raw.index("{"):])
except Exception:
    print(raw); sys.exit()
props = d["viewModel"]["properties"] if d.get("viewModel") else d["nested"][0]["viewModels"][0]["properties"]
v = {p["name"]: p.get("value") for p in props}
keys = sys.argv[1].split(",")
print("  " + "  ".join(f"{k}={round(v[k], 3) if isinstance(v.get(k), float) else v.get(k)}" for k in keys if k in v))
' "$KEYS"; }
dump() { # name, args...
  local name="$1"; shift
  printf '\n== %s\n' "$name"
  "$R" . --quiet --data-dump=- "$@" 2>&1 | show
}

echo "# orientation by width (landscape when width >= layoutBreakpoint, default 768)"
for vp in 320x568 360x640 390x844 430x932 600x960 767x1024 667x375 740x360 \
          768x1024 820x1180 1024x768 1280x720 1440x900 1920x1080 2560x1080 1366x600; do
  dump "$vp" --viewport=$vp --data=currentScreen=2 --advance=10
done

echo; echo "# the host can tune the breakpoint"
dump "1280x720, layoutBreakpoint=1400 -> portrait (short, side by side)" --viewport=1280x720 --data=layoutBreakpoint=1400 --advance=10
dump "767x1024, layoutBreakpoint=700 -> landscape" --viewport=767x1024 --data=layoutBreakpoint=700 --advance=10

echo; echo "# landscape 1280x720: tap zones use the real width (left third < 426.7), hold, keys"
dump "tap x=420 from scene 3 (expect 2, dir -1)" --viewport=1280x720 --data=currentScreen=3 --advance=30 --pointer=click@420,360 --advance=30
dump "tap x=440 from scene 3 (expect 4)" --viewport=1280x720 --data=currentScreen=3 --advance=30 --pointer=click@440,360 --advance=30
dump "tap x=1200 from scene 3 (expect 4)" --viewport=1280x720 --data=currentScreen=3 --advance=30 --pointer=click@1200,360 --advance=30
dump "hold 1.5s at x=900 then release (expect 3)" --viewport=1280x720 --data=currentScreen=3 --advance=30 --pointer=down@900,360 --advance=90 --pointer=up@900,360 --advance=10
dump "keys right right left (expect 2)" --viewport=1280x720 --advance=30 --key=right --advance=10 --key=right --advance=10 --key=left --advance=10
dump "continue button bottom-right (expect 2)" --viewport=1280x720 --advance=30 --pointer=click@1204,674 --advance=20
dump "1920x1080 continue button, chrome x1.5 (expect 2)" --viewport=1920x1080 --advance=30 --pointer=click@1806,1011 --advance=20

echo; echo "# landscape persona: the art crosses to the left of the spread on a spring"
dump "1280x720 8 -> 9, 10 frames in (_artX gliding)" --viewport=1280x720 --data=currentScreen=8 --advance=60 --key=right --advance=10
dump "1280x720 8 -> 9, 90 frames in (_artX settled left)" --viewport=1280x720 --data=currentScreen=8 --advance=60 --key=right --advance=90
dump "1280x720 9 -> 10, 90 frames in (_artX back right)" --viewport=1280x720 --data=currentScreen=9 --advance=60 --key=right --advance=90
dump "reduced motion 8 -> 9, 1 frame in (_artX snaps)" --viewport=1280x720 --data=reducedMotion=true --data=currentScreen=8 --advance=30 --key=right --advance=1

echo; echo "# resize across the breakpoint while the recap runs (KilnRecap nested in ResizeHarness:"
echo "# width 390 until frame 150, 1280 until frame 330, then 390 again)"
H="${TMPDIR:-/tmp}/kiln-resize-harness"
python3 tools/resize_harness.py "$H" --screen 4 >/dev/null
hdump() { local name="$1"; shift; printf '\n== %s\n' "$name"; "$R" "$H" --quiet --artboard=ResizeHarness --data-dump=- "$@" 2>&1 | show; }
hdump "scene 4, frame 120: portrait" --advance=120
hdump "scene 4, frame 160: just resized to 1280 (expect landscape, scene 4, 1 event)" --advance=160
hdump "scene 4, frame 300: settled landscape" --advance=300
hdump "scene 4, frame 480: back to 390 (expect portrait, scene 4, 1 event)" --advance=480
python3 tools/resize_harness.py "$H" --screen 2 >/dev/null
hdump "mid-transition: tap next at frame 140, resize at 150, frame 160 (expect 3, 2 events)" --advance=140 --pointer=click@300,400 --advance=20
hdump "mid-transition: same, frame 320 (settled on 3, landscape, 2 events)" --advance=140 --pointer=click@300,400 --advance=180
if [ -n "${SHOTS:-}" ]; then
  mkdir -p "$SHOTS"
  for f in 145 156 175 320; do
    "$R" "$H" --quiet --artboard=ResizeHarness --screenshot="$SHOTS/resize-mid-transition-f$f.png" --advance=140 --pointer=click@300,400 --advance=$((f - 140))
  done
fi
rm -rf "$H"
