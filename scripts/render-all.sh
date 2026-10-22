#!/usr/bin/env bash
# Re-render every app's portrait and landscape videos (apps/<app>/video.webm at
# 390x844, apps/<app>/video-landscape.webm at 1280x720), then the merged
# showcases (apps/showcase.webm, apps/showcase-landscape.webm), and exports each
# to the committed MP4 (the WebMs are the git-ignored working format).
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
  # shellcheck disable=SC2086
  "$here/render-video.py" "$app" --viewport 1280x720 \
    --output "$root/apps/$app/video-landscape.webm" ${RENDER_ARGS:-} || failed+=("$app (landscape)")
done

# shellcheck disable=SC2086
"$here/merge-videos.py" ${MERGE_ARGS:-}
"$here/merge-videos.py" --video video-landscape.webm --rows 2 --scale 0.35 \
  --output "$root/apps/showcase-landscape.webm"

# Export the committed MP4s.
"$here/export-mp4.sh"

if [ "${#failed[@]}" -gt 0 ]; then
  echo "failed: ${failed[*]}" >&2
  exit 1
fi
