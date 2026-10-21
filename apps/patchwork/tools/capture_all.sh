#!/bin/bash
# Regenerates every review capture under apps/patchwork/rive/captures/.
# Headless only (rive --screenshot); never opens the previewer window.
set -u
cd "$(dirname "$0")/../rive"
R=~/.rive/bin/rive
OUT=captures
mkdir -p $OUT/scenes $OUT/personas $OUT/transitions $OUT/fixtures $OUT/reduced-motion $OUT/states $OUT/viewports

shot() { # out [args...]
  local o=$1; shift
  $R . --quiet --screenshot="$o" "$@" >/dev/null 2>&1 || echo "FAILED $o"
}
taps() { # n -> forward taps, each followed by 70 frames
  local n=$1 a=(--advance=150)
  for ((i=0;i<n;i++)); do a+=(--pointer=click@300,420 --advance=70 --pointer=move@5,5); done
  echo "${a[@]}"
}
fx() { # fixture file -> --data args (one per line)
  local f=$1
  while IFS= read -r l; do case "$l" in ''|'#'*) ;; *) printf '%s\n' "$l";; esac; done < "$f"
}

# 1) ten settled scenes (sample fixture = authored defaults)
names=(01-invitation 02-hours 03-projects 04-community-days 05-garden 06-repairs 07-welcome 08-active-months 09-persona 10-summary)
for n in $(seq 0 9); do shot $OUT/scenes/${names[$n]}.png $(taps $n) --advance=200; done

# 2) personas (scene 9) and their summary cards
pn=("Neighborhood Weaver" "Quiet Helper" "Hands-on Builder" "Community Welcomer")
pd=("You help the pieces belong." "Your care shows up in small ways." "You enjoy making something useful together." "You make it easier to join in.")
pc=(FFCC7051 FFE9ACB2 FFF5EBDD FF4D8F83)
for k in 0 1 2 3; do
  shot $OUT/personas/persona-$k.png --data=personaIndex=$k "--data=personaName=${pn[$k]}" "--data=personaDescription=${pd[$k]}" --data=personaColor=${pc[$k]} $(taps 8) --advance=220
  shot $OUT/personas/persona-$k-reveal-mid.png --data=personaIndex=$k "--data=personaName=${pn[$k]}" "--data=personaDescription=${pd[$k]}" --data=personaColor=${pc[$k]} $(taps 7) --advance=10 --pointer=click@300,420 --advance=70
  shot $OUT/personas/persona-$k-summary.png --data=personaIndex=$k "--data=personaName=${pn[$k]}" "--data=personaDescription=${pd[$k]}" --data=personaColor=${pc[$k]} $(taps 9) --advance=220
done
shot $OUT/personas/persona-unknown-index-7-falls-back-to-0.png --data=personaIndex=7 $(taps 8) --advance=220

# 3) transitions: intermediate frames
for f in 6 12 18 24 32; do shot $OUT/transitions/forward-1to2-f$(printf %02d $f).png --advance=200 --pointer=click@300,420 --advance=$f; done
for f in 6 12 18 26 34; do shot $OUT/transitions/reverse-3to2-f$(printf %02d $f).png $(taps 2) --advance=100 --pointer=click@60,420 --advance=$f; done
for f in 4 14 26 40 60; do shot $OUT/transitions/carry-8to9-f$(printf %02d $f).png $(taps 7) --advance=100 --pointer=click@300,420 --advance=$f; done
for f in 4 14 30 52 80; do shot $OUT/transitions/carry-9to10-f$(printf %02d $f).png $(taps 8) --advance=100 --pointer=click@300,420 --advance=$f; done
for f in 20 40 60 90; do shot $OUT/transitions/entrance-s3-f$(printf %02d $f).png $(taps 1) --pointer=click@300,420 --advance=$f; done

# 4) reduced motion
shot $OUT/reduced-motion/rm-02-hours-settled.png --data=reducedMotion=true $(taps 1) --advance=30
shot $OUT/reduced-motion/rm-veil-mid-transition.png --data=reducedMotion=true --advance=150 --pointer=click@300,420 --advance=9
shot $OUT/reduced-motion/rm-09-persona.png --data=reducedMotion=true $(taps 8) --advance=30
shot $OUT/reduced-motion/rm-10-summary.png --data=reducedMotion=true $(taps 9) --advance=30

# 5) fixtures
mapfile_args() { local f=$1; local -a a=(); while IFS= read -r l; do a+=("$l"); done < <(fx "$f"); printf '%s\0' "${a[@]}"; }
run_fx() { # fixture out [extra...]
  local f=$1 o=$2; shift 2
  local -a a=(); while IFS= read -r -d '' l; do a+=("$l"); done < <(mapfile_args "$f")
  shot "$o" "${a[@]}" "$@"
}
run_fx ../fixtures/zero-user.args $OUT/fixtures/zero-user-01-intro.png --advance=200
run_fx ../fixtures/zero-user.args $OUT/fixtures/zero-user-10-summary.png $(taps 1) --advance=220
run_fx ../fixtures/extreme.args $OUT/fixtures/extreme-01-intro.png --advance=200
run_fx ../fixtures/extreme.args $OUT/fixtures/extreme-02-hours.png $(taps 1) --advance=200
run_fx ../fixtures/extreme.args $OUT/fixtures/extreme-06-repairs.png $(taps 5) --advance=200
run_fx ../fixtures/extreme.args $OUT/fixtures/extreme-09-persona.png $(taps 8) --advance=220
run_fx ../fixtures/extreme.args $OUT/fixtures/extreme-10-summary.png $(taps 9) --advance=220
shot $OUT/fixtures/hidden-3-4-progress-8-segments.png --data=showScreen3=false --data=showScreen4=false $(taps 2) --advance=200
shot $OUT/fixtures/runtime-update-hours-512.png --data=volunteerHours=512 $(taps 1) --advance=200

# 6) states
shot $OUT/states/thanks-flap-open-s1.png --advance=150 --pointer=click@283,298 --advance=28
shot $OUT/states/thanks-flap-open-summary.png $(taps 9) --advance=150 --pointer=click@323,236 --advance=28
shot $OUT/states/paused.png --advance=150 --pointer=click@346,772 --advance=60
shot $OUT/states/focus-ring-continue.png --advance=150 --key=tab --advance=4 --key=tab --advance=10
shot $OUT/states/share-capture-mode-card.png --data=shareCaptureMode=true $(taps 9) --advance=220
shot $OUT/states/share-card-name-included.png --data=shareIncludeName=true $(taps 9) --advance=220

# 7) viewports (host uses fit=contain on a fixed 390x844 artboard)
for v in 320x568 390x844 430x932 1280x800; do shot $OUT/viewports/viewport-$v.png --viewport=$v --fit=contain $(taps 1) --advance=200; done
echo done
