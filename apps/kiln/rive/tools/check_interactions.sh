#!/usr/bin/env bash
# Headless interaction checks for the Kiln recap. Prints the view-model values
# each scenario ends on. Run from anywhere: tools/check_interactions.sh
set -u
cd "$(dirname "$0")/.."
R="${RIVE:-$HOME/.rive/bin/rive}"
F='currentScreen,screenProgress,isPaused,_navDir,_holding,_screenChangedCount,_shareTappedCount,_recapFinishedCount,_finished,_seg*,_isEmpty,_personaVariant'
dump() { # name, args...
  local name="$1"; shift
  printf '\n== %s\n' "$name"
  "$R" . --quiet --data-dump=- --data-dump-filter="$F" "$@" 2>&1 | python3 -c '
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw[raw.index("{"):])
except Exception:
    print(raw); sys.exit()
vals = {p["name"]: p.get("value") for p in d["viewModel"]["properties"]}
segs = "".join("." if vals.get(f"_seg{i}") == 0 else "x" for i in range(1, 11))
keys = ["currentScreen", "screenProgress", "isPaused", "_navDir", "_holding", "_screenChangedCount",
        "_shareTappedCount", "_recapFinishedCount", "_finished", "_isEmpty", "_personaVariant"]
print("  " + "  ".join(f"{k}={round(vals[k],3) if isinstance(vals.get(k), float) else vals.get(k)}" for k in keys if k in vals))
print("  segments (. shown, x hidden): " + segs)
'
}
NEXT="--pointer=click@372,330"   # right two-thirds of the story area, clear of the turntable
BACK="--pointer=click@60,500"    # left third
GAP="--pointer=move@200,620"
dump "rest after 1s"                                --advance=1s
dump "tap forward once"                             --advance=1s $NEXT --advance=30
dump "rapid taps x5 (expect screen 6, 6 events)"     --advance=10 $NEXT $GAP $NEXT $GAP $NEXT $GAP $NEXT $GAP $NEXT --advance=90
dump "forward 3 then back 1 (expect 3, dir -1)"     --advance=10 $NEXT $GAP $NEXT $GAP $NEXT --advance=10 $BACK --advance=60
dump "hold 1.5s then release (no navigation)"       --advance=1s --pointer=down@330,500 --advance=90 --data-dump-filter="$F"
dump "hold released (still screen 1)"               --advance=1s --pointer=down@330,500 --advance=90 --pointer=up@330,500 --advance=10
dump "pause button (progress frozen)"               --advance=2s --pointer=click@96,798 --advance=3s
dump "pause then resume"                            --advance=2s --pointer=click@96,798 --advance=1s $GAP --pointer=click@96,798 --advance=1s
dump "continue button"                              --advance=1s --pointer=click@350,798 --advance=30
dump "previous button from 3"                       --data=currentScreen=3 --advance=1s --pointer=click@42,798 --advance=30
dump "keys: right right left space"                 --advance=30 --key=right --advance=10 --key=right --advance=10 --key=left --advance=10 --key=space --advance=10
dump "hidden 3,4,7 (segments adapt, skip)"          --data=showScreen3=false --data=showScreen4=false --data=showScreen7=false --advance=10 $NEXT $GAP $NEXT --advance=30
dump "auto-advance full run, 3s dwell (expect 10, finished once)" --data=autoAdvanceSeconds=3 --advance=60s
dump "auto-advance disabled (stays on 1)"           --data=autoAdvanceEnabled=false --advance=20s
dump "unsafe dwell 0.2s clamps to 3s (expect 2 after 6s)" --data=autoAdvanceSeconds=0.2 --advance=6s
dump "summary: share tap emits shareTapped"         --data=currentScreen=10 --advance=2s --pointer=click@120,798 --advance=10
dump "summary: replay resets latch"                 --data=currentScreen=10 --advance=2s --pointer=click@254,798 --advance=30
dump "new user: intro -> summary only"              --data=showScreen2=false --data=showScreen3=false --data=showScreen4=false --data=showScreen5=false --data=showScreen6=false --data=showScreen7=false --data=showScreen8=false --advance=10 $NEXT --advance=30
dump "unknown persona index 7 falls back to 0"      --data=personaIndex=7 --advance=10
dump "turntable drag on scene 2 never navigates"   --data=currentScreen=2 --advance=2s '--pointer=drag@200,560>320,560:12' --advance=30
dump "still tap on the vessel still navigates"     --data=currentScreen=2 --advance=2s --pointer=click@250,560 --advance=30
dump "invalid start screen 0 -> intro"              --data=currentScreen=0 --advance=10
