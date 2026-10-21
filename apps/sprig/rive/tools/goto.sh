#!/usr/bin/env bash
# tools/goto.sh <scene 1-10> <out.png> <frames> [extra rive flags]
# Click Continue (scene-1) times, 40 frames apart, then advance <frames> counted from the LAST click
# (so transition-..-fN.png really is N frames into the transition).
set -euo pipefail
cd "$(dirname "$0")/.."
k=$1; out=$2; settle=$3; shift 3
args=(--advance=30)
for ((i = 1; i < k; i++)); do
  args+=(--pointer=click@195,790)
  if ((i < k - 1)); then args+=(--advance=40); fi
done
"${RIVE:-$HOME/.rive/bin/rive}" . --screenshot="$out" "$@" "${args[@]}" --advance="$settle" >/dev/null 2>&1
