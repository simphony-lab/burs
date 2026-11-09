#!/usr/bin/env bash
# Prepares a render machine for LUNCH MONEY: Blender as a Python module, MakeHuman CC0 data, ambientCG textures.
# Usage: bash lunchmoney/worker_setup.sh [workdir]   -> then: source <workdir>/env.sh
set -euo pipefail
W="${1:-$HOME/lmwork}"
mkdir -p "$W/dl" "$W/tex"
cd "$W"
[ -x venv/bin/python ] || python3 -m venv venv
venv/bin/pip install -q bpy==5.2.3 pillow numpy
if [ ! -d dl/mpfb/data ]; then
  curl -sSL -m 600 -o dl/mpfb.zip "https://extensions.blender.org/download/sha256:c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad/add-on-mpfb-v2.0.18.zip"
  echo "c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad  dl/mpfb.zip" | sha256sum -c -
  mkdir -p dl/mpfb && (cd dl/mpfb && unzip -q ../mpfb.zip) && rm dl/mpfb.zip
fi
if [ ! -d dl/mhassets/skins ]; then
  curl -sSL -m 1200 -o dl/mh.zip "https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip"
  mkdir -p dl/mhassets && (cd dl/mhassets && unzip -q ../mh.zip) && rm dl/mh.zip
fi
for id in WoodFloor051 PaintedPlaster017 Plaster001 Wood051 Metal032 Metal049A Snow010A Snow013 Asphalt031 \
          PaintedPlaster006 PaintedMetal004 Metal063 Facade018A Concrete034 Tiles138; do
  [ -d "tex/$id" ] && continue
  curl -sSL -m 300 -o "tex/$id.zip" "https://ambientcg.com/get?file=${id}_1K-JPG.zip"
  mkdir -p "tex/$id" && (cd "tex/$id" && unzip -q "../$id.zip") && rm "tex/$id.zip"
done
cat > env.sh <<ENV
export LM_MPFB="$W/dl/mpfb/data"
export LM_ASSETS="$W/dl/mhassets"
export LM_TEX="$W/tex"
export LM_PY="$W/venv/bin/python"
ENV
ls /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf >/dev/null
echo "LUNCH MONEY worker ready: source $W/env.sh"
