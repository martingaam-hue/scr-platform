#!/usr/bin/env bash
# =============================================================================
# SCR Platform — HeyGen Clip Combiner
# =============================================================================
# Uses ffmpeg to combine multi-source clips into single scene background files.
# Run this BEFORE heygen_generate.py.
#
# Usage:
#   bash scripts/heygen_combine_clips.sh <clips_dir>
#
# Example:
#   bash scripts/heygen_combine_clips.sh ~/Desktop/scr_clips
#
# Input files expected (name them exactly):
#   clip01.mp4 through clip26.mp4
#
# Output files produced (ready for heygen_generate.py):
#   scene05_bg.mp4  through  scene21_bg.mp4
# =============================================================================

set -euo pipefail

CLIPS_DIR="${1:-./clips}"

if [ ! -d "$CLIPS_DIR" ]; then
  echo "ERROR: Directory not found: $CLIPS_DIR"
  echo "Usage: bash scripts/heygen_combine_clips.sh <clips_dir>"
  exit 1
fi

cd "$CLIPS_DIR"

# Check ffmpeg is available
if ! command -v ffmpeg &>/dev/null; then
  echo "ERROR: ffmpeg not found. Install with: brew install ffmpeg"
  exit 1
fi

echo "============================================"
echo "SCR Platform — HeyGen Clip Combiner"
echo "Working directory: $CLIPS_DIR"
echo "============================================"
echo ""

# ── Helper: copy single clip → scene file ────────────────────────────────────
single() {
  local src="$1" dst="$2"
  if [ ! -f "$src" ]; then
    echo "  MISSING: $src  (skipping $dst)"
    return
  fi
  if [ -f "$dst" ]; then
    echo "  EXISTS:  $dst  (skipping)"
    return
  fi
  echo "  Copying  $src → $dst"
  cp "$src" "$dst"
}

# ── Helper: concatenate multiple clips → scene file ──────────────────────────
combine() {
  local dst="$1"; shift
  local srcs=("$@")

  # Check all sources exist
  local missing=0
  for src in "${srcs[@]}"; do
    if [ ! -f "$src" ]; then
      echo "  MISSING: $src  (skipping $dst)"
      missing=1
    fi
  done
  [ "$missing" -eq 1 ] && return

  if [ -f "$dst" ]; then
    echo "  EXISTS:  $dst  (skipping)"
    return
  fi

  echo "  Combining $(IFS=' + '; echo "${srcs[*]}") → $dst"

  # Build ffmpeg concat list
  local concat_file
  concat_file=$(mktemp /tmp/heygen_concat_XXXXXX.txt)
  for src in "${srcs[@]}"; do
    echo "file '$PWD/$src'" >> "$concat_file"
  done

  ffmpeg -y \
    -f concat -safe 0 -i "$concat_file" \
    -c:v libx264 -preset fast -crf 18 \
    -c:a aac -b:a 192k \
    -movflags +faststart \
    "$dst" \
    -loglevel error

  rm -f "$concat_file"
  echo "    → Done ($(du -h "$dst" | cut -f1))"
}

# ── Single-clip scenes ────────────────────────────────────────────────────────
echo "Single-clip scenes:"
single "clip01.mp4" "scene05_bg.mp4"
single "clip02.mp4" "scene06_bg.mp4"
single "clip03.mp4" "scene07_bg.mp4"
single "clip04.mp4" "scene08_bg.mp4"
single "clip05.mp4" "scene09_bg.mp4"
single "clip06.mp4" "scene10_bg.mp4"
single "clip07.mp4" "scene11_bg.mp4"
single "clip08.mp4" "scene12_bg.mp4"
single "clip09.mp4" "scene13_bg.mp4"
single "clip12.mp4" "scene15_bg.mp4"
single "clip13.mp4" "scene16_bg.mp4"
single "clip26.mp4" "scene21_bg.mp4"

echo ""
echo "Multi-clip scenes (ffmpeg concat):"
combine "scene14_bg.mp4" "clip10.mp4" "clip11.mp4"
combine "scene17_bg.mp4" "clip14.mp4" "clip15.mp4"
combine "scene18_bg.mp4" "clip16.mp4" "clip17.mp4" "clip18.mp4"
combine "scene19_bg.mp4" "clip19.mp4" "clip20.mp4" "clip21.mp4"
combine "scene20_bg.mp4" "clip22.mp4" "clip23.mp4" "clip24.mp4" "clip25.mp4"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "Results:"
echo "============================================"
expected=(
  scene05_bg.mp4 scene06_bg.mp4 scene07_bg.mp4 scene08_bg.mp4
  scene09_bg.mp4 scene10_bg.mp4 scene11_bg.mp4 scene12_bg.mp4
  scene13_bg.mp4 scene14_bg.mp4 scene15_bg.mp4 scene16_bg.mp4
  scene17_bg.mp4 scene18_bg.mp4 scene19_bg.mp4 scene20_bg.mp4
  scene21_bg.mp4
)

ok=0; missing=0
for f in "${expected[@]}"; do
  if [ -f "$f" ]; then
    echo "  ✓  $f  ($(du -h "$f" | cut -f1))"
    ((ok++)) || true
  else
    echo "  ✗  $f  MISSING"
    ((missing++)) || true
  fi
done

echo ""
echo "  $ok / ${#expected[@]} scene files ready."

if [ "$missing" -gt 0 ]; then
  echo "  $missing file(s) missing — check that all clip0X.mp4 source files exist."
  exit 1
else
  echo ""
  echo "All scene files ready."
  echo "Next step:"
  echo "  export HEYGEN_API_KEY=your_key"
  echo "  python scripts/heygen_generate.py --list-avatars"
  echo "  python scripts/heygen_generate.py --list-voices"
  echo "  python scripts/heygen_generate.py --clips-dir $CLIPS_DIR --avatar-id ID --voice-id ID"
fi
