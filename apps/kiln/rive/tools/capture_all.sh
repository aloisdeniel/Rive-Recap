#!/usr/bin/env bash
# Regenerates every capture under captures/. Slow-ish (each shot is a headless run).
# Usage: tools/capture_all.sh [section...]   sections: settled personas transitions reduced fixtures responsive card video
set -u
cd "$(dirname "$0")/.."
ROOT="$PWD"
R="${RIVE:-$HOME/.rive/bin/rive}"
C="$ROOT/captures"
J="${JOBS:-8}"
SECTIONS="${*:-settled personas transitions reduced fixtures responsive card video}"
mkdir -p "$C"
NEXT="--pointer=click@372,300"
BACK="--pointer=click@40,300"
shot() { # out, args...
  local out="$1"; shift
  mkdir -p "$(dirname "$out")"
  "$R" "${PROJ:-.}" --quiet --screenshot="$out" "$@" >/dev/null 2>&1 || echo "failed: $out"
}
throttle() { while [ "$(jobs -rp | wc -l)" -ge "$J" ]; do sleep 0.2; done; }
variant() { # fixture name -> project copy with that default instance
  local v="$1" d="${TMPDIR:-/tmp}/kiln-variant-$1"
  rm -rf "$d"; mkdir -p "$d"
  cp -R rive.yaml scripts assets "$d"/
  python3 tools/gen_kiln.py --default "$v" --out "$d/scene.rml" >/dev/null
  echo "$d"
}
PERSONA_ROWS=(
  "--data=personaIndex=0 --data=personaName=Form\ Finder --data=personaDescription=You\ let\ the\ material\ lead. --data=personaColor=F2ECE2"
  "--data=personaIndex=1 --data=personaName=Glaze\ Alchemist --data=personaDescription=Always\ testing\ a\ little\ magic. --data=personaColor=3547A2"
  "--data=personaIndex=2 --data=personaName=Wheel\ Regular --data=personaDescription=You\ return\ to\ the\ rhythm\ of\ making. --data=personaColor=38322F"
  "--data=personaIndex=3 --data=personaName=Handbuilt\ Storyteller --data=personaDescription=Your\ hands\ leave\ a\ story\ in\ every\ shape. --data=personaColor=BC7057"
)
for s in $SECTIONS; do case "$s" in
settled)
  shot "$C/settled/scene-01.png" --advance=200 &
  for n in 2 3 4 5 6 7 8 9 10; do throttle; shot "$C/settled/scene-$(printf %02d $n).png" --data=currentScreen=$n --advance=260 & done; wait ;;
personas)
  for k in 0 1 2 3; do throttle
    eval "shot \"$C/personas/persona-$k-settled.png\" --data=currentScreen=8 ${PERSONA_ROWS[$k]} --advance=150 $NEXT --advance=260" &
    eval "shot \"$C/personas/persona-$k-reveal-f100.png\" --data=currentScreen=8 ${PERSONA_ROWS[$k]} --advance=150 $NEXT --advance=100" &
  done; wait ;;
transitions)
  for n in 1 2 3 4 5 6 7 8 9; do m=$((n+1)); for f in 8 20 40; do throttle
    shot "$C/transitions/forward-$(printf %02d $n)-to-$(printf %02d $m)-f$(printf %02d $f).png" --data=currentScreen=$n --advance=200 $NEXT --advance=$f & done; done
  for f in 8 20 40; do throttle; shot "$C/transitions/reverse-03-to-02-f$(printf %02d $f).png" --data=currentScreen=3 --advance=200 $BACK --advance=$f & done
  for f in 8 20 40; do throttle; shot "$C/transitions/replay-10-to-01-f$(printf %02d $f).png" --data=currentScreen=10 --advance=200 --pointer=click@254,798 --advance=$f & done
  wait ;;
reduced)
  for n in 1 2 5 9 10; do throttle; shot "$C/reduced-motion/scene-$(printf %02d $n)-settled.png" --data=reducedMotion=true --data=currentScreen=$n --advance=60 & done
  shot "$C/reduced-motion/forward-02-to-03-f06.png" --data=reducedMotion=true --data=currentScreen=2 --advance=60 $NEXT --advance=6 &
  wait ;;
fixtures)
  NU="$(variant NewUser)"; EX="$(variant Extreme)"
  PROJ="$NU" shot "$C/fixtures/new-user-01-intro.png" --advance=200 &
  PROJ="$NU" shot "$C/fixtures/new-user-10-summary.png" --advance=60 $NEXT --advance=260 &
  for n in 1 2 3 4 6 7 8 9 10; do throttle; PROJ="$EX" shot "$C/fixtures/extreme-$(printf %02d $n).png" --data=currentScreen=$n --advance=260 & done
  throttle; PROJ="$EX" shot "$C/fixtures/extreme-10-share-public.png" --data=currentScreen=10 --data=shareIncludeName=true --data=shareIncludeSensitiveValues=true --advance=260 &
  throttle; shot "$C/fixtures/runtime-update-before.png" --data=currentScreen=2 --advance=260 &
  throttle; shot "$C/fixtures/runtime-update-after-piecesMade-1234.png" --data=currentScreen=2 --data=piecesMade=1234 --advance=260 &
  throttle; shot "$C/fixtures/locale-de-DE-clay-1234.5.png" --data=currentScreen=6 --data=locale=de-DE --data=clayReclaimedKg=1234.5 --advance=260 &
  wait; rm -rf "$NU" "$EX" ;;
responsive)
  for vp in 320x568 430x932; do for n in 1 2 4 9 10; do throttle
    shot "$C/responsive/$vp-scene-$(printf %02d $n).png" --viewport=$vp --data=currentScreen=$n --advance=260 & done; done
  throttle; shot "$C/responsive/desktop-1280x800-contain-scene-02.png" --viewport=1280x800 --fit=contain --data=currentScreen=2 --advance=260 &
  wait ;;
card)
  shot "$C/share-card/sharecard-standalone-default-private.png" --artboard=ShareCard --advance=2 &
  shot "$C/share-card/sharecard-standalone-public.png" --artboard=ShareCard --data=shareIncludeName=true --data=shareIncludeSensitiveValues=true --advance=2 &
  wait ;;
video)
  # full auto-advance run sampled at 12 fps, stitched with ffmpeg (if present)
  V="${TMPDIR:-/tmp}/kiln-video"; rm -rf "$V"; mkdir -p "$V"
  FPS=8; DUR="${VIDEO_SECONDS:-47}"; N=$((DUR*FPS))
  for i in $(seq 0 $N); do throttle; f=$(( i * 60 / FPS + 1 ))
    shot "$V/f$(printf %05d $i).png" --data=autoAdvanceSeconds=3 --advance=$f & done; wait
  if command -v ffmpeg >/dev/null; then
    ffmpeg -y -loglevel error -framerate $FPS -i "$V/f%05d.png" -vf "scale=390:844,format=yuv420p" "$C/motion-preview-autoplay.mp4"
  fi ;;
esac; done
echo done
