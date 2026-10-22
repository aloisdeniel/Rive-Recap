#!/bin/sh
# Regenerates captures/ (PNG stills). Runs jobs in parallel.
cd "$(dirname "$0")/.."
C="python3 tools/capture.py one"
{
for s in 1 2 3 4 5 6 7 8 9 10; do n=$(printf %02d $s); echo "$C $s 3200 captures/settled/scene-$n.png"; done
for k in 0 1 2 3; do echo "$C 9 3400 captures/personas/persona-$k.png personaIndex=$k"; echo "$C 9 1500 captures/personas/persona-$k-reveal-mid.png personaIndex=$k"; done
for s in 2 3 4 5 6 7 8 9 10; do p=$((s-1)); a=$(printf %02d $p); b=$(printf %02d $s);
  for t in 120 330 520; do echo "$C $s $t captures/transitions/fwd-$a-to-$b-${t}ms.png"; done; done
for t in 0 450 750 1000 1300 2000; do echo "$C 1 $t captures/transitions/cover-open-${t}ms.png --data=currentScreen=1"; done
for t in 200 450 700 1000 1300; do echo "$C 4 $t captures/transitions/hero-04-moon-${t}ms.png"; done
for t in 200 500 800; do echo "$C 5 $t captures/transitions/carry-moon-04-to-05-${t}ms.png"; done
for t in 300 700 1100 1600; do echo "$C 10 $t captures/transitions/summary-assembly-${t}ms.png"; done
echo "$C 1 3000 captures/reduced-motion/scene-01.png reducedMotion=true"
echo "$C 2 100 captures/reduced-motion/scene-02-crossfade-100ms.png reducedMotion=true"
echo "$C 2 400 captures/reduced-motion/scene-02.png reducedMotion=true"
echo "$C 9 400 captures/reduced-motion/scene-09.png reducedMotion=true"
echo "$C 10 400 captures/reduced-motion/scene-10.png reducedMotion=true"
echo "$C 1 3000 captures/fixtures/zero-scene-01.png --fixture=zero"
echo "$C 2 3000 captures/fixtures/zero-summary.png --fixture=zero"
for s in 1 2 3 4 6 9 10; do n=$(printf %02d $s); echo "$C $s 3200 captures/fixtures/extreme-scene-$n.png --fixture=extreme"; done
} | xargs -P 4 -I{} sh -c "{}"
# back transitions and interaction states (custom gesture sequences)
R="$HOME/.rive/bin/rive ."
mkdir -p captures/interaction captures/transitions
$R --quiet --artboard=ShareCard --screenshot=captures/share-card-artboard.png --advance=10 &
$R --quiet --artboard=Cover --screenshot=captures/cover-artboard.png --advance=2 &
M="--pointer=move@200,300"
T="--pointer=click@300,420 $M --advance=900ms"
$R --quiet --screenshot=captures/transitions/back-03-to-02-250ms.png --advance=300ms $T $T --pointer=click@60,420 --advance=250ms &
$R --quiet --screenshot=captures/transitions/back-03-to-02-450ms.png --advance=300ms $T $T --pointer=click@60,420 --advance=450ms &
$R --quiet --screenshot=captures/transitions/back-10-to-09-300ms.png --data=currentScreen=10 --advance=2500ms --pointer=click@60,420 --advance=300ms &
$R --quiet --screenshot=captures/transitions/replay-10-to-01-450ms.png --data=currentScreen=10 --advance=2500ms --pointer=click@366,795 --advance=450ms &
$R --quiet --screenshot=captures/transitions/rapid-5-taps-250ms.png --data=autoAdvanceEnabled=false --advance=2s --key=right --advance=2 --key=right --advance=2 --key=right --advance=2 --key=right --advance=2 --key=right --advance=250ms &
wait
$R --quiet --screenshot=captures/interaction/paused.png --advance=1500ms --pointer=click@344,795 --advance=1s &
$R --quiet --screenshot=captures/interaction/hold-to-pause-mid-hold.png --advance=1200ms --pointer=down@300,420 --advance=900ms &
$R --quiet --screenshot=captures/interaction/focus-after-tab.png --advance=1500ms --key=tab --advance=300ms &
$R --quiet --screenshot=captures/interaction/runtime-update-booksFinished-77.png --data=booksFinished=77 --advance=300ms --pointer=click@300,420 --advance=3s &
$R --quiet --screenshot=captures/interaction/hidden-screens-2-3-progress.png --data=showScreen2=false --data=showScreen3=false --advance=300ms --pointer=click@300,420 --advance=3s &
wait
# the responsive matrix (16 sizes, one contact sheet per scene; needs Pillow)
python3 tools/capture_responsive.py
echo done
