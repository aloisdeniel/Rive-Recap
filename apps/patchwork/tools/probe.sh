#!/bin/bash
# probe.sh [rive args...] -> prints key values at the end
cd "$(dirname "$0")/../rive"
~/.rive/bin/rive . --data-dump=- --quiet "$@" 2>/dev/null | jq -c '[.viewModel.properties[] | select(.path|test("^(currentScreen|screenProgress|isPaused|_holdPaused|screenChangedCount|recapFinishedCount|shareTappedCount|_finishedLatch|_thanksOpen|_focusIndex)$")) | {(.path): .value}] | add'
