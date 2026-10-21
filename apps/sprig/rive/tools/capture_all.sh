#!/usr/bin/env bash
# Regenerates every capture under captures/ (stale PNGs are removed first). Requires the rive CLI.
# Scenes are reached by clicking Continue (tools/goto.sh); transition frames count from the last click.
set -euo pipefail
cd "$(dirname "$0")/.."
RIVE=${RIVE:-$HOME/.rive/bin/rive}
C=captures; mkdir -p "$C"
rm -f "$C"/*.png
tools/capture.sh "$C" >/dev/null
# personas (copy written with --data, as the host adapter would)
tools/goto.sh 9 "$C/persona-0-canopy-keeper.png" 260 --data=personaIndex=0
tools/goto.sh 9 "$C/persona-1-propagation-pro.png" 260 --data=personaIndex=1 "--data=personaName=Propagation Pro" "--data=personaDescription=You saw a new beginning in every cutting." --data=personaColor=FFA8CC72
tools/goto.sh 9 "$C/persona-2-patient-grower.png" 300 --data=personaIndex=2 "--data=personaName=Patient Grower" "--data=personaDescription=You gave growth the time it needed." --data=personaColor=FFF3AD7D
tools/goto.sh 9 "$C/persona-3-windowsill-wanderer.png" 260 --data=personaIndex=3 "--data=personaName=Windowsill Wanderer" "--data=personaDescription=You found possibility in every sunny corner." --data=personaColor=FF173E32
# signature transition: frame vine + leaf iris + 3D paper leaf across the camera
for f in 8 16 24 34; do tools/goto.sh 2 "$C/transition-1to2-f$f.png" $f; done
for f in 12 24; do tools/goto.sh 5 "$C/transition-4to5-f$f.png" $f; done
# reverse: the frame unweaves into the vine tip, the leaf sweeps back inner face first, the mask folds left
for f in 6 20 34; do "$RIVE" . --screenshot="$C/transition-back-4to3-f$f.png" --advance=30 --pointer=click@195,790 --advance=40 --pointer=click@195,790 --advance=40 --pointer=click@195,790 --advance=200 --pointer=click@48,790 --advance=$f >/dev/null 2>&1; done
# 3D hero moments mid-motion
"$RIVE" . --screenshot="$C/scene1-seed-closed-f8.png" --advance=8 >/dev/null 2>&1
tools/goto.sh 4 "$C/scene4-paper-bud-f30.png" 30
tools/goto.sh 4 "$C/scene4-opening-f60.png" 60
tools/goto.sh 9 "$C/scene9-seed-cradle-f30.png" 30
tools/goto.sh 2 "$C/scene2-unfurl-f50.png" 50
# reduced motion: short opacity fades, numbers final at once, no wipe / 3D sweep / idle motion
tools/goto.sh 2 "$C/reduced-motion-scene2-f6.png" 6 --data=reducedMotion=true
tools/goto.sh 4 "$C/reduced-motion-scene4.png" 40 --data=reducedMotion=true
# zero / new user: intro -> welcoming summary, no persona
Z=(--data=careMoments=0 --data=plantsNurtured=0 --data=newLeaves=0 --data=cuttingsRooted=0 --data=careStreak=0 --data=plantsShared=0 --data=activeMonths=0 "--data=userName=Sam")
for i in 2 3 4 5 6 7 8 9; do Z+=(--data=showScreen$i=false); done
tools/goto.sh 1 "$C/zero-user-intro.png" 170 "${Z[@]}"
tools/goto.sh 2 "$C/zero-user-summary.png" 200 "${Z[@]}"
# extreme values / long copy (40%+ longer strings)
X=(--data=careMoments=128940 --data=plantsNurtured=1204 --data=newLeaves=98765 --data=cuttingsRooted=4321 --data=careStreak=365 --data=activeMonths=12
   "--data=userName=Maximiliana Wilhelmina Featherstonehaugh-Okonkwo" "--data=introHeadline=Your whole 2026, told through Sprig"
   "--data=screen2Headline=Little rituals, repeated with care. Big, beautiful growth." "--data=screen2Support=Each and every gentle check-in made a little more room for something green."
   "--data=screen2Unit=care moments logged with love" --data=shareIncludeName=true)
tools/goto.sh 1 "$C/extreme-intro.png" 170 "${X[@]}"
tools/goto.sh 2 "$C/extreme-scene2.png" 170 "${X[@]}"
tools/goto.sh 6 "$C/extreme-scene6.png" 170 "${X[@]}"
tools/goto.sh 10 "$C/extreme-summary.png" 200 "${X[@]}"
# hidden scenes: 3,4,7 hidden -> 7 segments
tools/goto.sh 3 "$C/hidden-3-4-7-nav.png" 170 --data=showScreen3=false --data=showScreen4=false --data=showScreen7=false
# paused state
"$RIVE" . --screenshot="$C/paused-scene1.png" --advance=300 --pointer=click@342,790 --advance=200 >/dev/null 2>&1
# responsive checks (fixed 390x844 artboard, host fit = contain)
"$RIVE" . --screenshot="$C/viewport-320x568-contain.png" --viewport=320x568 --fit=contain --advance=170 >/dev/null 2>&1
"$RIVE" . --screenshot="$C/viewport-430x932-contain.png" --viewport=430x932 --fit=contain --advance=170 >/dev/null 2>&1
"$RIVE" . --screenshot="$C/viewport-desktop-1280x800-contain.png" --viewport=1280x800 --fit=contain --advance=170 >/dev/null 2>&1
echo done
