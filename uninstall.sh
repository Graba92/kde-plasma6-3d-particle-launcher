#!/usr/bin/env bash
set -euo pipefail

echo "==> Beende laufende Instanzen..."
pkill -f "python3.*jarvis_core.py" 2>/dev/null || true

echo "==> Entferne Dateien..."
sudo rm -rf /opt/jarvis-spatial-shell
sudo rm -f /usr/local/bin/jarvis-orb
rm -f "$HOME/.local/share/applications/jarvis-orb.desktop"

echo "==> Bereinige KDE-Shortcuts..."
SHORTCUTS_CONF="$HOME/.config/kglobalshortcutsrc"
if [ -f "$SHORTCUTS_CONF" ]; then
    sed -i '/\[jarvis-orb.desktop\]/,/^$/d' "$SHORTCUTS_CONF" 2>/dev/null || true
    qdbus org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel.reloadConfig 2>/dev/null || true
fi

echo "[OK] Jarvis Spatial Command Shell wurde vollständig deinstalliert."
