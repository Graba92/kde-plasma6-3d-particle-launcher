# 🌐 Jarvis Spatial Command Shell (v2.2)

[**Deutsch**](#-deutsch) | [**English**](#-english)

---

## 🇩🇪 Deutsch

Die **Jarvis Spatial Command Shell** ist ein hardwarebeschleunigtes, transparentes **3D-Partikel-Hologramm** und ein **Spatial Desktop Launcher** für Linux. Entwickelt für **CachyOS / Arch Linux, Fedora, Ubuntu/Debian** unter **KDE Plasma 6 (Wayland & X11)**.

Sie visualisiert Audio-Streams in Echtzeit (konzentrische Wasser-Schockwellen, Equalizer-Spikes, Pulse) sowie Systemauslastung (CPU/RAM) und bietet ein 3D-Kugelmenü mit 4 programmierbaren Direktstart-Slots.

### ✨ Kernfunktionen

* **100 % Transparent & Desktop-Verankert:** Verbleibt dauerhaft als Hintergrund-Element auf dem Wallpaper (`KeepBelow`), taucht nicht in Alt-Tab oder Taskleisten auf.
* **Spatial 4-Slot Launcher:** 1 zentraler Home-Core (`~`) + 3 frei belegbare Schnellstart-Slots für Ordner oder Systemwerkzeuge.
* **Hover Proximity Slowdown:** Nähert sich der Mauszeiger einem Knoten, bremst die Rotation automatisch sanft auf 15 % ab.
* **Holografischer Sub-Bubble Ring:** Schwebt der Cursor über einem Knoten, steigen 4 rotierende Sub-Orbit-Blasen mit Vektordrähten auf.
* **Sci-Fi HUD:** Projektion von Vektorlinien mit Zielpfad, Dateityp und Schnellaktionen bei Mouseover.
* **Echtzeit-PipeWire-FFT:** Greift direkt auf den Monitor-Sink deiner aktiven Soundkarte zu (HDMI, Klinke, DAC).
* **Entkoppeltes Control Deck (5 Tabs):** Einstellungsfenster dockt mit Abstand neben der Kugel an – kein Verdecken des Renderings beim Konfigurieren.

### 🎮 Steuerung & Tastenkürzel

| Taste / Aktion | Funktion |
| :--- | :--- |
| **`E`** | Schaltet den Bearbeitungsrahmen und das Zahnrad (**⚙**) AN oder AUS |
| **`C`** | Öffnet/Schließt das Control Deck jederzeit |
| **`Leertaste` / Doppelklick** | **Snap-to-Front:** Dreht die Kugel frontal zu den Slots aus |
| **Linksklick + Ziehen** | *(Rahmen AUS)*: Kugel frei im 3D-Raum drehen (Trackball) |
| **Mausrad** | Stufenloser 3D-Zoom der Kugel |
| **Klick auf Knoten** | Öffnet Ordner via `xdg-open` oder führt hinterlegtes Tool aus |
| **`Ctrl + Shift + J`** | Globaler System-Shortcut zum Starten/Beenden |
| **Terminal: `jarvis-orb`** | Toggelt die Shell unabhängig vom Terminal |

### 🚀 Installation

```bash
git clone [https://github.com/xxgrabaxx/jarvis-spatial-shell.git](https://github.com/xxgrabaxx/jarvis-spatial-shell.git)
cd jarvis-spatial-shell
chmod +x install.sh
./install.sh
