#!/bin/bash
# usage: tools/trans.sh <from scene> <frames after tap> <out.png> [next|back] [extra flags]
# Navigates to a scene, taps Continue (or Previous) and captures mid-transition.
cd "$(dirname "$0")/.."
N=$1; F=$2; OUT=$3; DIR=${4:-next}; shift 4
ARGS=(--advance=150)
for ((i=1;i<N;i++)); do ARGS+=(--pointer=click@260,790 --advance=190); done
if [ "$DIR" = back ]; then ARGS+=(--pointer=click@50,790 --advance=$F); else ARGS+=(--pointer=click@260,790 --advance=$F); fi
~/.rive/bin/rive . --screenshot="$OUT" "$@" "${ARGS[@]}" --quiet
