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

echo "failures: $fail"
exit $fail
