#!/bin/bash
# Regenerates captures/responsive/: the viewport matrix as contact sheets.
#   apps/patchwork/tools/capture_responsive.sh [jobs]
# One sheet per scene across all 16 sizes (portrait sizes first, then
# landscape, in the order listed below), plus mid-transition sheets per
# orientation and a fixtures sheet. Raw frames go to a temp dir; only the
# sheets are kept. Headless only; scenes are reached with Right-arrow presses,
# so the same input works at every size.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/../rive"
R=${RIVE:-$(command -v rive || echo ~/.rive/bin/rive)}
JOBS=${1:-3}
OUT=captures/responsive
RAW=$(mktemp -d "${TMPDIR:-/tmp}/patchwork-resp.XXXX")
PORTRAIT="320x568 360x640 390x844 430x932 600x960 767x1024 667x375 740x360"
LANDSCAPE="768x1024 820x1180 1024x768 1280x720 1440x900 1920x1080 2560x1080 1366x600"
rm -rf "$OUT"
mkdir -p "$OUT"

# shot OUT VIEWPORT SCENE SETTLE [extra args...]
shot() {
  local o=$1 v=$2 s=$3 settle=$4; shift 4
  local a=(--advance=150)
  for ((i = 1; i < s; i++)); do a+=(--key=right --advance=70); done
  for t in 1 2 3; do
    "$R" . --quiet --screenshot="$o" --viewport="$v" "${a[@]}" --advance="$settle" "$@" >/dev/null 2>&1 && return
    sleep 1
  done
  echo "FAILED $o"
}
export -f shot
export R RAW

# 1) every scene, settled, at every size
for v in $PORTRAIT $LANDSCAPE; do for s in 1 2 3 4 5 6 7 8 9 10; do echo "$RAW/s$s-$v.png $v $s 220"; done; done |
  xargs -P "$JOBS" -L 1 bash -c 'shot "$@"' _
names=(01-invitation 02-hours 03-projects 04-community-days 05-garden 06-repairs 07-welcome 08-active-months 09-persona 10-summary)
for s in 1 2 3 4 5 6 7 8 9 10; do
  imgs=(); for v in $PORTRAIT $LANDSCAPE; do imgs+=("$RAW/s$s-$v.png"); done
  python3 "$HERE/contact_sheet.py" "$OUT/scene-${names[$((s - 1))]}.png" "${imgs[@]}" --height 300 --row-width 3400
done

# 2) mid-transition frames, per orientation: the quilt fold (1 -> 2, sheet landing
#    and folding away), the 8 -> 9 carry and the 9 -> 10 bloom
TR="390x844 320x568 740x360 768x1024 1280x720 2560x1080"
for v in $TR; do
  echo "$RAW/t-fold10-$v.png $v 1 10 --key=right --advance=10"
  echo "$RAW/t-fold30-$v.png $v 1 10 --key=right --advance=30"
  echo "$RAW/t-carry89-$v.png $v 8 100 --key=right --advance=24"
  echo "$RAW/t-bloom910-$v.png $v 9 100 --key=right --advance=14"
  echo "$RAW/t-emblem910-$v.png $v 9 100 --key=right --advance=34"
done | xargs -P "$JOBS" -L 1 bash -c 'shot "$@"' _
for kind in fold10 fold30 carry89 bloom910 emblem910; do
  imgs=(); for v in $TR; do imgs+=("$RAW/t-$kind-$v.png"); done
  python3 "$HERE/contact_sheet.py" "$OUT/transition-$kind.png" "${imgs[@]}" --height 340 --row-width 3400
done

# 3) fixtures and personas in both orientations
fx() { while IFS= read -r l; do case "$l" in '' | '#'*) ;; *) printf '%s\n' "$l" ;; esac; done < "$1"; }
EX=(); while IFS= read -r l; do EX+=("$l"); done < <(fx ../fixtures/extreme.args)
ZU=(); while IFS= read -r l; do ZU+=("$l"); done < <(fx ../fixtures/zero-user.args)
for v in 390x844 1280x720; do
  shot "$RAW/f-ex2-$v.png" "$v" 2 200 "${EX[@]}" &
  shot "$RAW/f-ex9-$v.png" "$v" 9 220 "${EX[@]}" &
  shot "$RAW/f-ex10-$v.png" "$v" 10 220 "${EX[@]}" &
  shot "$RAW/f-zu10-$v.png" "$v" 2 220 "${ZU[@]}" &
  wait
  shot "$RAW/f-p1-$v.png" "$v" 9 220 --data=personaIndex=1 "--data=personaName=Quiet Helper" \
    "--data=personaDescription=Your care shows up in small ways." --data=personaColor=FFE9ACB2 &
  shot "$RAW/f-p2-$v.png" "$v" 9 220 --data=personaIndex=2 "--data=personaName=Hands-on Builder" \
    "--data=personaDescription=You enjoy making something useful together." --data=personaColor=FFF5EBDD &
  shot "$RAW/f-p3-$v.png" "$v" 9 220 --data=personaIndex=3 "--data=personaName=Community Welcomer" \
    "--data=personaDescription=You make it easier to join in." --data=personaColor=FF4D8F83 &
  shot "$RAW/f-rm10-$v.png" "$v" 10 30 --data=reducedMotion=true &
  wait
done
for v in 390x844 1280x720; do
  python3 "$HERE/contact_sheet.py" "$OUT/fixtures-personas-$v.png" "$RAW"/f-ex2-$v.png "$RAW"/f-ex9-$v.png \
    "$RAW"/f-ex10-$v.png "$RAW"/f-zu10-$v.png "$RAW"/f-p1-$v.png "$RAW"/f-p2-$v.png "$RAW"/f-p3-$v.png \
    "$RAW"/f-rm10-$v.png --height 360 --row-width 3400
done
rm -rf "$RAW"
ls "$OUT"
