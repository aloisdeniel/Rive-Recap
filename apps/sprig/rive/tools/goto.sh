#!/usr/bin/env bash
# tools/goto.sh <scene 1-10> <out.png> <settle-frames> [extra rive flags]  -- click Continue (scene-1) times then settle
set -euo pipefail
cd "$(dirname "$0")/.."
k=$1; out=$2; settle=$3; shift 3
args=(--advance=30)
for ((i = 1; i < k; i++)); do args+=(--pointer=click@195,790 --advance=40); done
"${RIVE:-$HOME/.rive/bin/rive}" . --screenshot="$out" "$@" "${args[@]}" --advance="$settle" >/dev/null 2>&1
