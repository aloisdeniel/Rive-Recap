#!/usr/bin/env bash
# Headless captures of the Sprig recap. Usage: tools/capture.sh <outdir> [extra rive flags...]
# Scenes are reached by clicking Continue (195,790); each click is followed by enough frames for the
# 450-850 ms wipe and the 1.8 s entrance to settle.
set -euo pipefail
cd "$(dirname "$0")/.."
RIVE=${RIVE:-$HOME/.rive/bin/rive}
OUT=${1:-captures}; shift || true
mkdir -p "$OUT"
for k in $(seq 1 10); do
  args=(--advance=30)
  for ((i = 1; i < k; i++)); do args+=(--pointer=click@195,790 --advance=40); done
  "$RIVE" . --screenshot="$OUT/scene-$(printf %02d "$k").png" "${args[@]}" --advance=170 "$@" >/dev/null 2>&1
  echo "scene $k -> $OUT/scene-$(printf %02d "$k").png"
done
