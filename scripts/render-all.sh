#!/usr/bin/env bash
# Re-render every app's video (apps/<app>/video.webm), then the merged
# showcase (apps/showcase.webm), plus git-ignored MP4 copies of each.
#
#   scripts/render-all.sh [app ...]       # default: every app with a rive/ project
#
# Extra options for render-video.py can be passed through RENDER_ARGS, and for
# merge-videos.py through MERGE_ARGS, e.g. RENDER_ARGS="--fps 20" scripts/render-all.sh
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$here")"

if [ "$#" -gt 0 ]; then
  apps=("$@")
else
  apps=()
  for project in "$root"/apps/*/rive/rive.yaml; do
    apps+=("$(basename "$(dirname "$(dirname "$project")")")")
  done
fi

failed=()
for app in "${apps[@]}"; do
  # shellcheck disable=SC2086
  "$here/render-video.py" "$app" ${RENDER_ARGS:-} || failed+=("$app")
done

# shellcheck disable=SC2086
"$here/merge-videos.py" ${MERGE_ARGS:-}

# MP4 copies for platforms without WebM support (git-ignored).
"$here/export-mp4.sh"

if [ "${#failed[@]}" -gt 0 ]; then
  echo "failed: ${failed[*]}" >&2
  exit 1
fi
