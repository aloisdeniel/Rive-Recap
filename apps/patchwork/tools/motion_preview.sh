#!/bin/bash
# Renders a full motion preview (all ten scenes, a reverse step, the thanks flap,
# replay) as headless frames at 12 fps and encodes captures/motion-preview.mp4.
set -u
cd "$(dirname "$0")/../rive"
FR=${FRAMES_DIR:-/tmp/patchwork-frames}; mkdir -p "$FR"; rm -f "$FR"/*.png
# timeline (60 fps frames): tap forward every 200 frames; at 3 one back-tap; thanks flap on scene 1
events=()            # "frame:kind"
events+=("60:thanks")
t=200
for i in 1 2 3; do events+=("$t:next"); t=$((t+200)); done
events+=("$t:prev"); t=$((t+160))
for i in 1 2 3 4 5 6 7; do events+=("$t:next"); t=$((t+200)); done
END=$((t+180))
n=0
for ((f=1; f<END; f+=5)); do
  args=(); last=0
  for e in "${events[@]}"; do
    ef=${e%%:*}; kind=${e##*:}
    [ $ef -ge $f ] && break
    args+=(--advance=$((ef-last)))
    case $kind in
      next) args+=(--pointer=click@300,420 --pointer=move@5,5);;
      prev) args+=(--pointer=click@60,420 --pointer=move@5,5);;
      thanks) args+=(--pointer=click@283,298 --pointer=move@5,5);;
    esac
    last=$((ef+2))
  done
  rem=$((f-last)); [ $rem -lt 1 ] && rem=1
  args+=(--advance=$rem)
  ~/.rive/bin/rive . --quiet --screenshot="$FR/$(printf %05d $n).png" "${args[@]}" >/dev/null 2>&1
  n=$((n+1))
done
ffmpeg -y -loglevel error -framerate 12 -i "$FR/%05d.png" -vf "scale=390:844,format=yuv420p" -c:v libx264 -crf 20 captures/motion-preview.mp4
echo "frames: $n"
