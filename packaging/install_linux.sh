#!/usr/bin/env bash
# Install the built Linux executable into ~/.local (menu entry + PATH).
#   bash packaging/install_linux.sh
set -euo pipefail
cd "$(dirname "$0")/.."
BIN="$HOME/.local/bin/lookthrough-studio"
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/256x256/apps"
cp dist/lookthrough-studio "$BIN"
chmod +x "$BIN"
cp packaging/lookthrough-studio.desktop "$HOME/.local/share/applications/"
cp packaging/icon-256.png "$HOME/.local/share/icons/hicolor/256x256/apps/lookthrough-studio.png"
echo "Installed $BIN"
echo "Run 'lookthrough-studio' from a terminal, or find it in your app menu."
