#!/usr/bin/env bash
# Live preview of the Nocturne recap with a fixture pushed into UserRecap.
#   tools/preview.sh                 # sample fixture (the file's default instance)
#   tools/preview.sh new-user        # zero / new-user fixture
#   tools/preview.sh extreme-long-copy
# Extra flags pass through, e.g.  tools/preview.sh sample --data=reducedMotion=true
set -euo pipefail
cd "$(dirname "$0")/.."
fixture="${1:-sample}"; shift || true
args=()
while IFS= read -r line; do args+=("$line"); done < <(python3 - "$fixture" <<'PY'
import json, sys
d = json.load(open(f"fixtures/{sys.argv[1]}.json"))
for k, v in d.items():
    if isinstance(v, bool): v = "true" if v else "false"
    if k == "personaColor": v = str(v).lstrip("#")
    print(f"--data={k}={v}")
PY
)
exec "${RIVE:-$HOME/.rive/bin/rive}" . "${args[@]}" "$@"
