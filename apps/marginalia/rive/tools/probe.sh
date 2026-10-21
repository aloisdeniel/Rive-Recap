#!/bin/sh
# usage: tools/probe.sh <rive args...>  -> prints key UserRecap values after the run
cd "$(dirname "$0")/.." && ~/.rive/bin/rive . --data-dump=- "$@" 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
keys=('currentScreen','screenProgress','isPaused','_motionPaused','visibleScreenCount','visibleScreenIndex','booksFinishedText','personaName','isSharing','_dbgScreenEvents','_dbgShareEvents','_dbgFinishedEvents')
v={p['name']:p.get('value') for p in d['viewModel']['properties']}
print(' '.join(f'{k}={v.get(k)}' for k in keys))"
