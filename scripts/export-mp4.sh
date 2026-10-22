#!/usr/bin/env bash
# Convert the WebM recap renders to H.264 MP4, the format committed in the repo
# (and accepted everywhere, e.g. X/Twitter uploads). Writes each MP4 next to its WebM:
#   apps/<app>/video.mp4, apps/<app>/video-landscape.mp4, apps/showcase.mp4 and
#   apps/showcase-landscape.mp4
# The WebMs are the git-ignored working format; re-run this after rendering.
#
#   scripts/export-mp4.sh [file.webm ...]    # default: every app video + both showcases
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$#" -gt 0 ]; then
  inputs=("$@")
else
  inputs=()
  for webm in "$root"/apps/*/video.webm "$root"/apps/*/video-landscape.webm \
    "$root"/apps/showcase.webm "$root"/apps/showcase-landscape.webm; do
    [ -f "$webm" ] && inputs+=("$webm")
  done
fi

for webm in "${inputs[@]}"; do
  mp4="${webm%.webm}.mp4"
  ffmpeg -y -loglevel error -i "$webm" \
    -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p \
    -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" -movflags +faststart -an "$mp4"
  echo "wrote ${mp4#"$root"/} ($(du -h "$mp4" | cut -f1))"
done
