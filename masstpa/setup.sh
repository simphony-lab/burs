#!/usr/bin/env bash
# Installs Blender as a Python module (bpy) + Pillow into ./venv and downloads the Unifont font.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv venv
./venv/bin/pip install -q bpy==5.2.3 pillow numpy
mkdir -p fonts
[ -f fonts/unifont.otf ] || curl -sSfL -o fonts/unifont.otf \
  https://unifoundry.com/pub/unifont/unifont-16.0.04/font-builds/unifont-16.0.04.otf
echo "ok"
