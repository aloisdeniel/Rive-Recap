#!/bin/bash
# shootfx.sh FIXTURE.args OUT.png TAPS [settle]  -- shoot.sh with --data lines read from a fixture file
fx=$1; out=$2; taps=$3; settle=${4:-200}
EX=()
while IFS= read -r l; do case "$l" in ''|'#'*) ;; *) EX+=("$l");; esac; done < "$fx"
"$(dirname "$0")/shoot.sh" "$out" "$taps" "$settle" "${EX[@]}"
