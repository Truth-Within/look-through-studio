#!/usr/bin/env bash
# Build the Linux desktop app (single-file executable) from the project root:
#   bash packaging/build_linux.sh
# -> dist/lookthrough-studio
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install -r requirements.txt pyinstaller
python3 packaging/make_icons.py
pyinstaller packaging/studio-linux.spec --clean --noconfirm
echo
echo "Built: dist/lookthrough-studio"
echo "Run it:  ./dist/lookthrough-studio        # opens http://127.0.0.1:8080"
echo "Install: bash packaging/install_linux.sh"
