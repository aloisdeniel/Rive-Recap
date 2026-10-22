#!/bin/bash
# check.sh — headless behaviour checks for the Patchwork recap (the README's
# "Verification performed" table, as assertions). Exit code = number of failures.
#   apps/patchwork/tools/check.sh
set -u
cd "$(dirname "$0")/../rive"
R=${RIVE:-$(command -v rive || echo ~/.rive/bin/rive)}
fail=0
F='^(currentScreen|screenProgress|isPaused|_holdPaused|screenChangedCount|recapFinishedCount|shareTappedCount|_finishedLatch|_thanksOpen|_focusIndex|_noActivity)$'

dump() { "$R" . --data-dump=- --quiet "$@" 2>/dev/null | jq -c "[.viewModel.properties[] | select(.path|test(\"$F\")) | {(.path): .value}] | add"; }

# expect "name" '<jq boolean expression>' [rive args...]
expect() {
  local name=$1 expr=$2; shift 2
  local got; got=$(dump "$@")
  if [ -n "$got" ] && echo "$got" | jq -e "$expr" >/dev/null 2>&1; then
    printf 'ok    %s\n' "$name"
  else
    printf 'FAIL  %s\n      %s\n' "$name" "$got"; fail=$((fail + 1))
  fi
}

TAP=(--pointer=click@300,420 --pointer=move@5,5)
BACK=(--pointer=click@60,420 --pointer=move@5,5)

expect "full auto-advance ends on summary, 10 screens, finished once" \
  '.currentScreen==10 and .screenChangedCount==10 and .recapFinishedCount==1' --advance=120s
expect "hidden 3,4,9 are skipped (7 scenes entered)" \
  '.currentScreen==10 and .screenChangedCount==7 and .recapFinishedCount==1' \
  --data=showScreen3=false --data=showScreen4=false --data=showScreen9=false --advance=100s
expect "zero user: intro -> welcoming summary" \
  '.currentScreen==10 and ._noActivity==true and .screenChangedCount==2' \
  $(sed -n 's/^\(--data=.*\)$/\1/p' ../fixtures/zero-user.args | tr '\n' ' ') --data=autoAdvanceEnabled=false \
  --advance=150 "${TAP[@]}" --advance=200
expect "5 rapid taps land on 6 with exactly 6 screenChanged" \
  '.currentScreen==6 and .screenChangedCount==6' --data=autoAdvanceEnabled=false --advance=150 \
  "${TAP[@]}" --advance=3 "${TAP[@]}" --advance=3 "${TAP[@]}" --advance=3 "${TAP[@]}" --advance=3 "${TAP[@]}" --advance=200
expect "right arrow x3, left x1 lands on 3" \
  '.currentScreen==3' --data=autoAdvanceEnabled=false --advance=150 --key=right --advance=60 --key=right --advance=60 \
  --key=right --advance=60 --key=left --advance=80
expect "hold 90 frames pauses, release does not navigate" \
  '.currentScreen==1 and ._holdPaused==false' --advance=150 --pointer=down@300,420 --advance=90 --pointer=up@300,420 --advance=30
expect "hold is active while held" \
  '._holdPaused==true and .currentScreen==1' --advance=150 --pointer=down@300,420 --advance=90
expect "pause button freezes progress" \
  '.isPaused==true and .currentScreen==1 and .screenProgress<0.5' --advance=150 --pointer=click@346,772 --advance=10s
expect "space toggles pause" '.isPaused==true' --advance=150 --key=space --advance=10
expect "tab tab focuses Continue, enter activates" \
  '._focusIndex==2 and .currentScreen==2' --data=autoAdvanceEnabled=false --advance=150 --key=tab --advance=4 --key=tab \
  --advance=4 --key=enter --advance=120
expect "previous on scene 1 is a no-op" '.currentScreen==1 and .screenChangedCount==1' --advance=150 "${BACK[@]}" --advance=80
expect "share counts once; replay returns to 1 and clears the latch" \
  '.shareTappedCount==1 and .recapFinishedCount==1 and .currentScreen==1 and ._finishedLatch==false' \
  --data=autoAdvanceSeconds=3 --advance=60s --pointer=click@139,772 --advance=30 --pointer=click@259,772 --advance=120
expect "summary back + forward does not re-fire recapFinished" \
  '.recapFinishedCount==1 and .currentScreen==10' --data=autoAdvanceSeconds=3 --advance=60s --key=left --advance=90 \
  --key=right --advance=200
expect "thanks patch lifts without navigating" \
  '.currentScreen==1 and .screenChangedCount==1' --data=autoAdvanceEnabled=false --advance=150 --pointer=click@283,298 --advance=20
expect "reduced motion: full run still reaches summary" \
  '.currentScreen==10 and .screenChangedCount==10 and .recapFinishedCount==1' --data=reducedMotion=true --advance=100s

# ---- responsive layout -------------------------------------------------------
# Orientation is a pure width breakpoint (landscape when width >= layoutBreakpoint).
F='^(currentScreen|screenProgress|isPaused|_holdPaused|screenChangedCount|recapFinishedCount|shareTappedCount|_finishedLatch|_thanksOpen|_focusIndex|_noActivity|_landscape|_split|_settled|_vw|_vh|_cardWide)$'
expect "767 wide is portrait (tall)" '._landscape==false and ._split==false' --viewport=767x1024 --advance=10
expect "768 wide is landscape (tall canvas)" '._landscape==true' --viewport=768x1024 --advance=10
expect "740x360 is portrait (short: copy beside the hero)" '._landscape==false and ._split==true' --viewport=740x360 --advance=10
expect "2560x1080 is landscape" '._landscape==true and ._vw==2560' --viewport=2560x1080 --advance=10
expect "host-tuned breakpoint: 1024 wide with layoutBreakpoint=1100 is portrait" '._landscape==false' \
  --viewport=1024x768 --data=layoutBreakpoint=1100 --advance=10
expect "landscape: full auto-advance ends on summary, postcard card" \
  '.currentScreen==10 and .screenChangedCount==10 and .recapFinishedCount==1 and ._cardWide==true' \
  --viewport=1280x720 --advance=120s
expect "landscape: Right arrow x3, Left x1 lands on 3" '.currentScreen==3' --viewport=1280x720 \
  --data=autoAdvanceEnabled=false --advance=150 --key=right --advance=60 --key=right --advance=60 --key=right --advance=60 \
  --key=left --advance=80
expect "landscape: right two-thirds tap advances, left third goes back (real width)" '.currentScreen==2 and .screenChangedCount==4' \
  --viewport=1280x720 --data=autoAdvanceEnabled=false --advance=150 --pointer=click@1000,300 --pointer=move@5,5 --advance=70 \
  --pointer=click@900,300 --pointer=move@5,5 --advance=70 --pointer=click@300,300 --pointer=move@5,5 --advance=90
expect "landscape: hold pauses, release does not navigate" '.currentScreen==1 and ._holdPaused==false' --viewport=1280x720 \
  --advance=150 --pointer=down@1000,300 --advance=90 --pointer=up@1000,300 --advance=30
expect "landscape: pause button follows the page (1195,648 at 1280x720)" '.isPaused==true and .currentScreen==1' \
  --viewport=1280x720 --advance=150 --pointer=click@1195,648 --advance=60
expect "short portrait 740x360: taps and arrows navigate" '.currentScreen==3' --viewport=740x360 \
  --data=autoAdvanceEnabled=false --advance=150 --pointer=click@600,150 --pointer=move@5,5 --advance=70 --key=right --advance=80
expect "landscape reduced motion: full run reaches summary" \
  '.currentScreen==10 and .screenChangedCount==10 and .recapFinishedCount==1' --viewport=1440x900 --data=reducedMotion=true --advance=100s

# Mid-scene resizes across the threshold. The CLI's --viewport is fixed for a
# run, so a harness artboard (tools/resize_harness.rml, generated) nests the
# recap in a box whose size is keyed: portrait 600x900 -> landscape 1200x800 at
# frame 300 -> portrait 700x900 at 480 -> landscape 1280x720 at 600. It is spliced
# into a temporary copy of the project; the shipped .riv never contains it.
HX=$(mktemp -d "${TMPDIR:-/tmp}/patchwork-harness.XXXX")
cp -R rive.yaml scripts shaders assets "$HX"/
python3 - "$HX" <<'PY'
import sys
d = sys.argv[1]
s = open("scene.rml").read()
h = open("../tools/resize_harness.rml").read()
i = s.rindex("</Rive>")
open(d + "/scene.rml", "w").write(s[:i] + h + s[i:])
PY
hdump() { (cd "$HX" && "$R" . --artboard="Resize harness" --viewport=1280x900 --data-dump=- --quiet "$@" 2>/dev/null) \
  | jq -c "[.viewModel.properties[] | select(.path|test(\"$F\")) | {(.path): .value}] | add"; }
hexpect() {
  local name=$1 expr=$2; shift 2
  local got; got=$(hdump "$@")
  if [ -n "$got" ] && echo "$got" | jq -e "$expr" >/dev/null 2>&1; then
    printf 'ok    %s\n' "$name"
  else
    printf 'FAIL  %s\n      %s\n' "$name" "$got"; fail=$((fail + 1))
  fi
}
hexpect "resize portrait->landscape while settled keeps scene 2" \
  '.currentScreen==2 and .screenChangedCount==2 and ._landscape==true and ._vw==1200 and ._settled==true' \
  --data=autoAdvanceEnabled=false --advance=150 --key=right --advance=270
hexpect "resize during a fold (frame 300) lands on 3, one event per scene, settles" \
  '.currentScreen==3 and .screenChangedCount==3 and ._landscape==true and ._settled==true' \
  --data=autoAdvanceEnabled=false --advance=150 --key=right --advance=143 --key=right --advance=170
hexpect "back across the threshold (frame 480) keeps scene 3 and settles in portrait" \
  '.currentScreen==3 and .screenChangedCount==3 and ._landscape==false and ._vw==700 and ._settled==true' \
  --data=autoAdvanceEnabled=false --advance=150 --key=right --advance=143 --key=right --advance=260
hexpect "auto-advance keeps its timing across three resizes (3 s dwell)" \
  '.screenChangedCount==.currentScreen and ._landscape==true and ._vw==1280' --data=autoAdvanceSeconds=3 --advance=700
rm -rf "$HX"

echo "failures: $fail"
exit $fail
