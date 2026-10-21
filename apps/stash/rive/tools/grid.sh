#!/bin/sh
# usage: tools/grid.sh <outdir> [extra rive flags...]  -- settled capture of every scene + contact sheets
set -e
OUT=$1; shift
mkdir -p "$OUT"
R=${RIVE:-$HOME/.rive/bin/rive}
for k in 1 2 3 4 5 6 7 8 9 10; do
  "$R" . --screenshot="$OUT/scene$(printf %02d $k).png" --data=currentScreen=$k --data=_count1=1 --data=_count2=1 "$@" --advance=2.6s >/dev/null 2>&1 &
done
wait
ffmpeg -loglevel error -y -i "$OUT/scene01.png" -i "$OUT/scene02.png" -i "$OUT/scene03.png" -i "$OUT/scene04.png" -i "$OUT/scene05.png" \
  -filter_complex "hstack=inputs=5,scale=1300:-1" "$OUT/sheet-1-5.png"
ffmpeg -loglevel error -y -i "$OUT/scene06.png" -i "$OUT/scene07.png" -i "$OUT/scene08.png" -i "$OUT/scene09.png" -i "$OUT/scene10.png" \
  -filter_complex "hstack=inputs=5,scale=1300:-1" "$OUT/sheet-6-10.png"
