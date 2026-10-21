#!/bin/bash
# usage: tools/shot.sh <scene 1-10> <out.png> [extra rive flags...]
# Navigates headlessly with the Continue button and captures the settled scene.
cd "$(dirname "$0")/.."
N=$1; OUT=$2; shift 2
ARGS=(--advance=150)
for ((i=1;i<N;i++)); do ARGS+=(--pointer=click@260,790 --advance=190); done
~/.rive/bin/rive . --screenshot="$OUT" "$@" "${ARGS[@]}" --quiet
