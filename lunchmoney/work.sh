#!/usr/bin/env bash
# Render worker job: renders the given shots of one scene with 4 processes, encodes each shot to
# lunchmoney/renders/<scene>_<shot>.mp4 and pushes it to the current branch.
# Usage: bash lunchmoney/work.sh <workdir> <scene> <shot,shot,...>
set -uo pipefail
W="$1"; SCENE="$2"; SHOTS="$3"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
source "$W/env.sh"
cd "$REPO/lunchmoney"
OUT="$W/frames"
mkdir -p "$OUT" renders
for p in 0 1 2 3; do
  "$LM_PY" render_episode.py --scene "$SCENE" --shots "$SHOTS" --part $p --parts 4 --threads 1 --out "$OUT" \
    > "$W/log_${SCENE}_$p.txt" 2>&1 &
done
wait
for SHOT in ${SHOTS//,/ }; do
  RANGE=$(python3 -c "
import episode_plan as P
p = P.SCENES['$SCENE']()
for s, a, b in p.shots:
    if s == '$SHOT': print(int(round(a*24))+1, min(int(round(b*24)), p.frames))")
  set -- $RANGE
  A=$1; B=$2
  LIST="$W/list_${SHOT}.txt"; : > "$LIST"
  missing=0
  for f in $(seq $A $B); do
    fn=$(printf "%s/%s/f%05d.png" "$OUT" "$SCENE" $f)
    if [ -f "$fn" ]; then echo "file '$fn'" >> "$LIST"; else missing=$((missing+1)); fi
  done
  echo "shot $SHOT frames $A-$B missing $missing"
  ffmpeg -v error -y -r 24 -f concat -safe 0 -i "$LIST" -c:v libx264 -preset medium -crf 12 -pix_fmt yuv420p \
    -r 24 "renders/${SCENE}_${SHOT}.mp4"
done
cd "$REPO"
for i in 1 2 3 4 5; do
  git pull -q --rebase origin "$(git rev-parse --abbrev-ref HEAD)" || true
  git add lunchmoney/renders/${SCENE}_*.mp4
  git commit -q -m "Render ${SCENE} shots ${SHOTS}" || true
  if git push -q origin HEAD; then echo "pushed ${SCENE} ${SHOTS}"; break; fi
  sleep $((i * 5))
done
