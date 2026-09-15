[🇩🇪 Zur deutschen Dokumentation wechseln](README_DE.md) | [🇬🇧 Switch to English Documentation](README.md)

# 🌐 Jarvis Spatial Command Shell (v2.2)

<p align="center">
  <img src="preview.png" alt="Jarvis Spatial Command Shell Hologram" width="850">
</p>

<p align="center">
  <a href="https://github.com/Graba92/kde-plasma6-3d-particle-launcher"><img src="https://img.shields.io/badge/GitHub-Graba92%2Fkde--plasma6--3d--particle--launcher-blue?logo=github" alt="GitHub"></a>
  <img src="https://img.shields.io/badge/Platform-CachyOS%20%7C%20Arch%20%7C%20Fedora%20%7C%20Debian-blue?logo=linux" alt="Linux">
  <img src="https://img.shields.io/badge/Desktop-KDE%20Plasma%206%20%7C%20Wayland%20%26%20X11-3399ff?logo=kde" alt="KDE">
  <img src="https://img.shields.io/badge/Python-3.10%2B-yellow?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt6-green?logo=qt" alt="PyQt6">
  <img src="https://img.shields.io/badge/Audio-PipeWire%20Realtime%20FFT-purple" alt="PipeWire">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
</p>

<p align="center">
  <b>🎬 <a href="demo.mp4">Watch Demo Video (MP4)</a></b>
</p>

> The **Jarvis Spatial Command Shell** is a hardware-accelerated, transparent **3D particle hologram** and **spatial desktop launcher** for Linux. Engineered specifically for **CachyOS / Arch Linux, Fedora, and Ubuntu/Debian** under **KDE Plasma 6 (Wayland & X11)**.
>
> It visualizes real-time PipeWire audio streams (wave ripples, equalizer spikes, acoustic pulse) alongside system telemetry (CPU/RAM) and features a 3D spherical menu with 4 programmable quick-launch slots.

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [Controls & Keybindings](#-controls--keybindings)
3. [Architecture & File Structure](#-architecture--file-structure)
4. [Installation & Quickstart](#-installation--quickstart)
5. [Configuration (Control Deck)](#-configuration-control-deck)
6. [Uninstallation](#-uninstallation)
7. [License](#-license)

---

## ✨ Key Features

* **100% Transparent & Desktop-Anchored:** Permanently resides on your wallpaper layer (`KeepBelow`), never appearing in Alt-Tab switchers or window taskbars.
* **Spatial 4-Slot Launcher:** 1 central Home Core (`~`) + 3 freely assignable quick-launch slots for folders or system utilities.
* **Hover Proximity Slowdown:** Smoothly decelerates sphere rotation down to 15% whenever your mouse pointer approaches an interactive node.
* **Holographic Sub-Bubble Ring:** Hovering over any node dynamically spawns 4 revolving sub-orbit bubbles with animated vector wiring.
* **Sci-Fi HUD Projection:** Renders crisp vector lines detailing destination paths, node types, and execution statuses on mouseover.
* **Real-Time PipeWire Audio FFT:** Direct, zero-latency monitoring of your active soundcard sink (HDMI, analog, USB DAC).
* **Decoupled Control Deck (5 Tabs):** Floating configuration console docks above/beside the sphere without obstructing rendering during adjustments.

---

## 🎮 Controls & Keybindings

| Key / Gesture | Action |
| :--- | :--- |
| **`E`** | Toggle edit frame and settings gear (**⚙**) ON or OFF |
| **`C`** | Open / Close the floating Control Deck at any time |
| **Spacebar** / Double-Click | **Snap-to-Front:** Aligns sphere frontally towards interactive slots |
| **Left Click + Drag** | *(Edit OFF)*: Freely rotate sphere in 3D space (Virtual Trackball) |
| **Mouse Wheel** | Stepless 3D zoom of the particle sphere |
| **Click on Node** | Launches folder via `xdg-open` or executes designated executable |
| **`Ctrl` + `Shift` + `J`** | Global system-wide shortcut to toggle or launch the shell |
| **Terminal: `jarvis-orb`** | Launch or toggle the shell daemon independently from CLI |

---

## 🏛️ Architecture & File Structure

```text
jarvis-spatial-shell/
├── jarvis_core.py              # Master PyQt6 3D engine, Math3D, PipeWire FFT & Control Deck
├── install.sh                  # Multi-distro installer (Arch/CachyOS, Fedora, Debian/Ubuntu, openSUSE)
├── uninstall.sh                # Clean uninstaller script
├── preview.png                 # High-resolution HUD preview screenshot
├── demo.gif                    # Animated demonstration
├── demo.mp4                    # High-definition video demo
├── LICENSE                     # MIT License
├── README.md                   # English documentation (this file)
└── README_DE.md                # German documentation
```

---

## 🚀 Installation & Quickstart

### 1. Automated Installer (Recommended)

Run the included universal installer. It detects your distribution, installs required dependencies, and registers the system-wide binary:

```bash
git clone https://github.com/Graba92/kde-plasma6-3d-particle-launcher.git
cd kde-plasma6-3d-particle-launcher
chmod +x install.sh
./install.sh
```

### 2. Manual Installation & Dependencies

**For CachyOS / Arch Linux:**
```bash
sudo pacman -S --needed python python-pyqt6 python-psutil pipewire wireplumber
python jarvis_core.py
```

**For Fedora:**
```bash
sudo dnf install -y python3 python3-pyqt6 python3-psutil pipewire pulseaudio-utils
python3 jarvis_core.py
```

**For Ubuntu / Debian:**
```bash
sudo apt update && sudo apt install -y python3 python3-pyqt6 python3-psutil pipewire
python3 jarvis_core.py
```

---

## ⚙️ Configuration (Control Deck)

Press **`C`** while the shell is running or click the gear icon (**⚙**) to reveal the **Control Deck**:

1. **General:** Sphere diameter, particle density, rotation inertia, snap angle.
2. **Audio FFT:** PipeWire sensitivity, frequency response bands, waveform ripples, and particle glow.
3. **Slots & Shortcuts:** Assign destination paths to core and sub-slots (file manager, terminal, web apps, custom scripts).
4. **Telemetry:** CPU and RAM polling intervals, Sci-Fi HUD opacity.
5. **Autostart:** 1-click registration of systemd user services for automatic startup upon Plasma login.

---

## 🗑️ Uninstallation

To cleanly remove the shell and its binaries from your system:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

---

## 📜 License

Distributed under the [MIT License](LICENSE) — Created by [Graba92](https://github.com/Graba92).
