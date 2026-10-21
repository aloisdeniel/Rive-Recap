#!/bin/bash
# shoot.sh OUT.png TAPS [settle_frames] [extra rive args...]
# Advances through TAPS forward taps (each followed by 70 frames), then settles and captures.
out=$1; taps=$2; settle=${3:-160}; shift 3
cd "$(dirname "$0")/../rive"
args=(--advance=150)
for ((i=0;i<taps;i++)); do args+=(--pointer=click@300,420 --advance=70 --pointer=move@5,5); done
~/.rive/bin/rive . --screenshot="$out" --quiet "$@" "${args[@]}" --advance=$settle 2>&1 | grep -vE "^\[.*rive  (built|showing|viewport|wrote|deferred)" 
