#!/usr/bin/env bash
# Regenerates every capture under captures/. Requires the rive CLI.
set -euo pipefail
cd "$(dirname "$0")/.."
C=captures; mkdir -p "$C"
tools/capture.sh "$C" >/dev/null
P=(personaName personaDescription personaColor)
tools/goto.sh 9 "$C/persona-0-canopy-keeper.png" 260 --data=personaIndex=0
tools/goto.sh 9 "$C/persona-1-propagation-pro.png" 260 --data=personaIndex=1 "--data=personaName=Propagation Pro" "--data=personaDescription=You saw a new beginning in every cutting." --data=personaColor=FFA8CC72
tools/goto.sh 9 "$C/persona-2-patient-grower.png" 300 --data=personaIndex=2 "--data=personaName=Patient Grower" "--data=personaDescription=You gave growth the time it needed." --data=personaColor=FFF3AD7D
tools/goto.sh 9 "$C/persona-3-windowsill-wanderer.png" 260 --data=personaIndex=3 "--data=personaName=Windowsill Wanderer" "--data=personaDescription=You found possibility in every sunny corner." --data=personaColor=FF173E32
for f in 4 14 24 34; do tools/goto.sh 2 "$C/transition-1to2-f$f.png" $f; done
for f in 10 24; do tools/goto.sh 6 "$C/transition-5to6-f$f.png" $f; done
# reverse (back) transition 3 -> 2
for f in 8 20 32; do ~/.rive/bin/rive . --screenshot="$C/transition-back-3to2-f$f.png" --advance=30 --pointer=click@195,790 --advance=40 --pointer=click@195,790 --advance=150 --pointer=click@48,790 --advance=$f >/dev/null 2>&1; done
# reduced motion: entrance and transition become short fades, numbers final immediately
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
~/.rive/bin/rive . --screenshot="$C/paused-scene1.png" --advance=300 --pointer=click@342,790 --advance=200 >/dev/null 2>&1
# responsive checks (fixed 390x844 artboard, host fit = contain)
~/.rive/bin/rive . --screenshot="$C/viewport-320x568-contain.png" --viewport=320x568 --fit=contain --advance=170 >/dev/null 2>&1
~/.rive/bin/rive . --screenshot="$C/viewport-430x932-contain.png" --viewport=430x932 --fit=contain --advance=170 >/dev/null 2>&1
~/.rive/bin/rive . --screenshot="$C/viewport-desktop-1280x800-contain.png" --viewport=1280x800 --fit=contain --advance=170 >/dev/null 2>&1
echo done
