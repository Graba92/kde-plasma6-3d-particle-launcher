#!/usr/bin/env bash
# ==============================================================================
# UNIVERSAL INSTALLER FOR JARVIS SPATIAL COMMAND SHELL
# Supported: Arch/CachyOS, Fedora, Debian/Ubuntu, openSUSE
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_BIN="/usr/local/bin/jarvis-orb"
APP_DIR="/opt/jarvis-spatial-shell"

echo -e "${BLUE}==> [1/5] Erkenne Linux-Distribution & installiere Abhängigkeiten...${NC}"

install_dependencies() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_ID="${ID:-unknown}"
        OS_LIKE="${ID_LIKE:-}"
    else
        echo -e "${RED}[FEHLER] /etc/os-release nicht gefunden.${NC}"
        exit 1
    fi

    echo -e "    Erkanntes System: ${GREEN}$NAME${NC}"

    case "$OS_ID" in
        arch|cachyos|endeavouros|manjaro)
            echo "    Verwende pacman..."
            sudo pacman -S --needed --noconfirm python python-pyqt6 python-psutil pipewire wireplumber
            ;;
        fedora)
            echo "    Verwende dnf..."
            sudo dnf install -y python3 python3-pyqt6 python3-psutil pipewire pulseaudio-utils
            ;;
        ubuntu|debian|pop|linuxmint)
            echo "    Verwende apt..."
            sudo apt-get update
            sudo apt-get install -y python3 python3-pyqt6 python3-psutil pipewire pulseaudio-utils
            ;;
        opensuse*|suse)
            echo "    Verwende zypper..."
            sudo zypper install -y python3 python3-qt6 python3-psutil pipewire pulseaudio-utils
            ;;
        *)
            if echo "$OS_LIKE" | grep -q "arch"; then
                sudo pacman -S --needed --noconfirm python python-pyqt6 python-psutil pipewire wireplumber
            elif echo "$OS_LIKE" | grep -q "debian"; then
                sudo apt-get update && sudo apt-get install -y python3 python3-pyqt6 python3-psutil pipewire pulseaudio-utils
            elif echo "$OS_LIKE" | grep -q "fedora"; then
                sudo dnf install -y python3 python3-pyqt6 python3-psutil pipewire pulseaudio-utils
            else
                echo -e "${RED}[WARNUNG] Unbekannte Distribution:$OS_ID. Bitte Python3, PyQt6, psutil und PipeWire manuell prüfen.${NC}"
            fi
            ;;
    esac
}

install_dependencies

echo -e "${BLUE}==> [2/5] Kopiere Core-Dateien nach $APP_DIR...${NC}"
sudo mkdir -p "$APP_DIR"
sudo cp "$SCRIPT_DIR/jarvis_core.py" "$APP_DIR/"
sudo chmod +x "$APP_DIR/jarvis_core.py"

echo -e "${BLUE}==> [3/5] Erstelle globalen Toggle-Befehl $TARGET_BIN...${NC}"
sudo tee "$TARGET_BIN" > /dev/null << 'EOB'
#!/usr/bin/env bash
PID=$(pgrep -f "python3.*jarvis_core.py" || true)

if [ -n "$PID" ]; then
    kill $PID 2>/dev/null || true
else
    export QT_QPA_PLATFORM="wayland;xcb"
    nohup python3 /opt/jarvis-spatial-shell/jarvis_core.py >/dev/null 2>&1 &
fi
EOB
sudo chmod +x "$TARGET_BIN"

echo -e "${BLUE}==> [4/5] Richte Desktop-Launcher & KDE-Regeln ein...${NC}"
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat << EOD > "$DESKTOP_DIR/jarvis-orb.desktop"
[Desktop Entry]
Type=Application
Name=Jarvis Spatial Core
Comment=Jarvis 3D Particle Visualizer and Command Shell
Exec=/usr/local/bin/jarvis-orb
Icon=utilities-terminal
Terminal=false
Categories=Utility;
StartupNotify=false
X-KDE-GlobalAccel-CommandShortcut=true
EOD
chmod +x "$DESKTOP_DIR/jarvis-orb.desktop"

# KWin Rule für Plasma 6 Wallpaper-Layer
KWIN_RULES="$HOME/.config/kwinrulesrc"
if [ -f "$KWIN_RULES" ] || command -v kbuildsycoca6 >/dev/null 2>&1; then
    if ! grep -q "JarvisSpatialShellV2" "$KWIN_RULES" 2>/dev/null; then
        cat << 'EOR' >> "$KWIN_RULES"

[JarvisSpatialShellV2]
Description=Keep Jarvis Spatial Shell on Desktop Layer
above=false
aboverule=2
below=true
belowrule=2
noborder=true
noborderrule=2
skiptaskbar=true
skiptaskbarrule=2
skippager=true
skippagerrule=2
wmclass=jarvis_core.py
wmclassmatch=1
EOR
        qdbus org.kde.KWin /KWin reconfigure 2>/dev/null || true
    fi
fi

# Shortcut Ctrl+Shift+J für KDE verankern
SHORTCUTS_CONF="$HOME/.config/kglobalshortcutsrc"
if [ -d "$(dirname "$SHORTCUTS_CONF")" ]; then
    if [ -f "$SHORTCUTS_CONF" ]; then
        sed -i '/\[jarvis-orb.desktop\]/,/^$/d' "$SHORTCUTS_CONF" 2>/dev/null || true
    fi
    cat << 'EOS' >> "$SHORTCUTS_CONF"

[jarvis-orb.desktop]
_k_friendly_name=Jarvis Spatial Core
_launch=Ctrl+Shift+J,none,Jarvis Spatial Core
EOS
    kbuildsycoca6 2>/dev/null || true
    qdbus org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel.reloadConfig 2>/dev/null || true
fi

echo -e "${BLUE}==> [5/5] Starte Jarvis Shell im Hintergrund...${NC}"
pkill -f "python3.*jarvis_core.py" 2>/dev/null || true
sleep 0.5
"$TARGET_BIN"

echo -e "\n${GREEN}[OK] INSTALLATION ERFOLGREICH BEENDET!${NC}"
echo "--------------------------------------------------------"
echo "Befehl:   jarvis-orb (überall im Terminal)"
echo "Hotkey:   Ctrl+Shift+J (systemweit in KDE Plasma)"
echo "Tasten:   'E' = Bearbeiten | 'C' = Einstellungs-Menü | 'Space' = Zentrieren"
echo "--------------------------------------------------------"
