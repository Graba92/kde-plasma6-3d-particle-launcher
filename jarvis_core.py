#!/usr/bin/env python3
"""
Jarvis Spatial Command Shell
High-Performance 3D Particle Visualizer & Spatial Desktop Launcher
Author: Matthias Haase (xxgrabaxx)
License: MIT
"""

import sys
import os
import json
import math
import random
import subprocess
import struct
import shutil
import colorsys
import psutil
from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets

CONFIG_DIR = Path.home() / ".config" / "jarvis-orb"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "particle_count": 1200,
    "base_particle_size": 2.0,
    "sphere_scale": 0.35,
    "color_idx": 0,
    "color_flow": True,
    "roam_enabled": False,
    "cpu_turbulence": 1.0,
    "rot_speed": 1.0,
    "ram_coupling": 1.0,
    "wave_direction": 1,
    "trigger_thresh": 0.14,
    "ripple_strength": 3.2,
    "ripple_area": 0.45,
    "ripple_speed": 0.08,
    "max_drops": 4,
    "active_mode": "Ripple",
    "manual_override": False,
    "edit_mode": False,
    "hotkey": "Ctrl+Shift+J",
    "slots": [
        {"name": "Home Core", "path": str(Path.home()), "type": "folder", "locked": True},
        {"name": "Slot 1: Scripts", "path": str(Path.home() / "Scripts"), "type": "folder", "locked": False},
        {"name": "Slot 2: Terminal", "path": "konsole", "type": "tool", "locked": False},
        {"name": "Slot 3: Projects", "path": str(Path.home()), "type": "folder", "locked": False}
    ]
}

def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    data.setdefault(k, v)
                return data
        except Exception:
            pass
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

class AudioMonitor(QtCore.QThread):
    fft_updated = QtCore.pyqtSignal(float, float, float, float)

    def __init__(self):
        super().__init__()
        self.running = True

    def get_sink(self):
        try:
            s = subprocess.check_output(["pactl", "get-default-sink"], text=True, timeout=1).strip()
            if s:
                return f"{s}.monitor"
        except Exception:
            pass
        return "@DEFAULT_MONITOR@"

    def run(self):
        src = self.get_sink()
        cmd = ["parec", "-d", src, "--channels=1", "--rate=44100", "--format=s16le"] if shutil.which("parec") else \
              ["pw-record", f"--target={src}", "--channels=1", "--rate=44100", "--format=s16", "-"]
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=2048)
        except Exception:
            return

        chunk = 512
        b_read = chunk * 2
        while self.running:
            raw = p.stdout.read(b_read)
            if not raw or len(raw) < b_read:
                continue
            try:
                shorts = struct.unpack(f"{chunk}h", raw)
                t_sum = sum(s * s for s in shorts)
                rms = min(1.0, (math.sqrt(t_sum / chunk) / 22000.0) ** 0.85 * 3.5)

                b_sum = sum(shorts[i] * shorts[i] for i in range(0, chunk, 4))
                bass = min(1.0, (math.sqrt(b_sum / (chunk // 4)) / 20000.0) ** 0.85 * 3.8)

                h_sum = sum((shorts[i] - shorts[i - 1]) ** 2 for i in range(1, chunk))
                highs = min(1.0, (math.sqrt(h_sum / chunk) / 26000.0) ** 0.85 * 3.8)

                mids = min(1.0, max(0.0, rms * 1.2 - (bass * 0.5 + highs * 0.5)))
                self.fft_updated.emit(bass, mids, highs, rms)
            except Exception:
                pass
        p.terminate()
        p.wait()

    def stop(self):
        self.running = False
        self.wait()

class TelemetryWorker(QtCore.QThread):
    stats_updated = QtCore.pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while self.running:
            self.stats_updated.emit(psutil.cpu_percent(interval=None), psutil.virtual_memory().percent)
            self.msleep(35)

    def stop(self):
        self.running = False
        self.wait()

class Particle:
    __slots__ = ['phi', 'theta', 'size_mod', 'cluster_weight', 'nx', 'ny', 'nz', 'x', 'y', 'z']
    def __init__(self):
        self.phi = math.acos(2.0 * random.random() - 1.0)
        self.theta = random.random() * 2.0 * math.pi
        d = random.random()
        if d < 0.70:
            self.size_mod = random.uniform(0.5, 0.9)
            self.cluster_weight = 0.6
        elif d < 0.90:
            self.size_mod = random.uniform(1.1, 1.5)
            self.cluster_weight = 1.0
        else:
            self.size_mod = random.uniform(2.0, 3.0)
            self.cluster_weight = 1.8

        self.nx = math.sin(self.phi) * math.cos(self.theta)
        self.ny = math.sin(self.phi) * math.sin(self.theta)
        self.nz = math.cos(self.phi)
        self.x = self.y = self.z = 0.0

class RippleDrop:
    __slots__ = ['center_nx', 'center_ny', 'center_nz', 'radius', 'strength', 'speed', 'decay', 'area_scale', 'direction']
    def __init__(self, strength, speed, area_scale, direction):
        phi = math.acos(2.0 * random.random() - 1.0)
        theta = random.random() * 2.0 * math.pi
        self.center_nx = math.sin(phi) * math.cos(theta)
        self.center_ny = math.sin(phi) * math.sin(theta)
        self.center_nz = math.cos(phi)
        self.radius = 0.0
        self.strength = strength
        self.speed = speed
        self.area_scale = area_scale
        self.direction = direction
        self.decay = 0.945

    def advance(self):
        self.radius += self.speed
        self.strength *= self.decay
        return self.strength > 0.02 and self.radius < 3.2

class CommandNode:
    def __init__(self, slot_idx, label, path, n_type, polar_phi, polar_theta):
        self.slot_idx = slot_idx
        self.label = label
        self.path = path
        self.n_type = n_type
        self.phi = polar_phi
        self.theta = polar_theta
        self.nx = math.sin(self.phi) * math.cos(self.theta)
        self.ny = math.sin(self.phi) * math.sin(self.theta)
        self.nz = math.cos(self.phi)
        self.proj_x = 0.0
        self.proj_y = 0.0
        self.proj_z = 0.0
        self.bubble_progress = 0.0

class ControlDeckWindow(QtWidgets.QWidget):
    def __init__(self, parent_core):
        super().__init__()
        self.core = parent_core
        self.setWindowFlags(QtCore.Qt.WindowType.Tool | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Jarvis Control Deck v2.2")
        self.setFixedSize(460, 600)
        self.setStyleSheet("""
            QWidget {
                background: rgba(10, 16, 26, 250);
                color: #cbeeff;
                font-family: monospace;
                font-size: 11px;
            }
            QTabWidget::pane {
                border: 1px solid rgba(0, 240, 255, 120);
                border-radius: 4px;
                background: #09131e;
            }
            QTabBar::tab {
                background: #0c1a28;
                color: #79a8c2;
                padding: 7px 11px;
                border: 1px solid #162f44;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #142e47;
                color: #00f0ff;
                border: 1px solid #00f0ff;
                border-bottom: none;
            }
            QLabel { border: none; font-size: 11px; }
            QSlider::groove:horizontal { height: 5px; background: #162c3f; border-radius: 2px; }
            QSlider::handle:horizontal { background: #00f0ff; width: 14px; margin: -5px 0; border-radius: 7px; }
            QPushButton {
                background: #122538;
                color: #00f0ff;
                border: 1px solid #00f0ff;
                border-radius: 3px;
                padding: 6px;
                font-weight: bold;
                min-height: 18px;
            }
            QPushButton:hover { background: #00f0ff; color: #080e16; }
            QLineEdit {
                background: #060e17;
                border: 1px solid #1f4360;
                border-radius: 3px;
                padding: 5px;
                color: #00f0ff;
                min-height: 18px;
            }
            QTextEdit {
                background: #060d16;
                border: 1px solid #16364d;
                border-radius: 4px;
                padding: 8px;
                color: #a2d2eb;
            }
            QScrollArea { border: none; background: transparent; }
            QGroupBox {
                border: 1px solid #1a3c56;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: bold;
                color: #00f0ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                background: #09131e;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: Optik
        t1 = QtWidgets.QWidget()
        l1 = QtWidgets.QVBoxLayout(t1)
        l1.setContentsMargins(10, 10, 10, 10)
        l1.setSpacing(8)

        self.btn_edit = QtWidgets.QPushButton(f"Bearbeitungsmodus: {'AN' if self.core.cfg['edit_mode'] else 'AUS'}")
        self.btn_edit.clicked.connect(self.toggle_edit)
        l1.addWidget(self.btn_edit)

        btn_col = QtWidgets.QPushButton("Farbe umschalten (Palette)")
        btn_col.clicked.connect(self.cycle_color)
        l1.addWidget(btn_col)

        self.btn_flow = QtWidgets.QPushButton(f"Farb-Flow: {'AN' if self.core.cfg['color_flow'] else 'AUS'}")
        self.btn_flow.clicked.connect(self.toggle_flow)
        l1.addWidget(self.btn_flow)

        self.lbl_den = QtWidgets.QLabel(f"Partikeldichte: {self.core.cfg['particle_count']}")
        l1.addWidget(self.lbl_den)
        s_den = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_den.setRange(200, 3000)
        s_den.setValue(self.core.cfg["particle_count"])
        s_den.valueChanged.connect(self.set_den)
        l1.addWidget(s_den)

        self.lbl_sz = QtWidgets.QLabel(f"Partikelgröße: {self.core.cfg['base_particle_size']:.1f}")
        l1.addWidget(self.lbl_sz)
        s_sz = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_sz.setRange(8, 50)
        s_sz.setValue(int(self.core.cfg["base_particle_size"] * 10))
        s_sz.valueChanged.connect(self.set_sz)
        l1.addWidget(s_sz)

        self.lbl_scale = QtWidgets.QLabel(f"Sphären-Skalierung: {self.core.cfg['sphere_scale']:.2f}")
        l1.addWidget(self.lbl_scale)
        s_sc = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_sc.setRange(20, 48)
        s_sc.setValue(int(self.core.cfg["sphere_scale"] * 100))
        s_sc.valueChanged.connect(self.set_scale)
        l1.addWidget(s_sc)

        l1.addStretch()
        tabs.addTab(t1, "Optik")

        # Tab 2: Audio & Physik
        t2 = QtWidgets.QWidget()
        l2 = QtWidgets.QVBoxLayout(t2)
        l2.setContentsMargins(10, 10, 10, 10)
        l2.setSpacing(7)

        self.btn_dir = QtWidgets.QPushButton(f"Wellen: {'AUSSEN' if self.core.cfg['wave_direction'] == 1 else 'INNEN'}")
        self.btn_dir.clicked.connect(self.toggle_dir)
        l2.addWidget(self.btn_dir)

        self.lbl_thr = QtWidgets.QLabel(f"Auslöse-Schwelle: {self.core.cfg['trigger_thresh']:.2f}")
        l2.addWidget(self.lbl_thr)
        s_thr = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_thr.setRange(2, 60)
        s_thr.setValue(int(self.core.cfg["trigger_thresh"] * 100))
        s_thr.valueChanged.connect(self.set_thr)
        l2.addWidget(s_thr)

        self.lbl_rip = QtWidgets.QLabel(f"Wellen-Stärke: {self.core.cfg['ripple_strength']:.1f}x")
        l2.addWidget(self.lbl_rip)
        s_rip = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_rip.setRange(5, 100)
        s_rip.setValue(int(self.core.cfg["ripple_strength"] * 10))
        s_rip.valueChanged.connect(self.set_rip)
        l2.addWidget(s_rip)

        self.lbl_area = QtWidgets.QLabel(f"Wellen-Breite: {self.core.cfg['ripple_area']:.2f}")
        l2.addWidget(self.lbl_area)
        s_ar = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_ar.setRange(15, 95)
        s_ar.setValue(int(self.core.cfg["ripple_area"] * 100))
        s_ar.valueChanged.connect(self.set_ar)
        l2.addWidget(s_ar)

        self.lbl_spd = QtWidgets.QLabel(f"Ausbreitungs-Tempo: {self.core.cfg['ripple_speed']:.2f}")
        l2.addWidget(self.lbl_spd)
        s_spd = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_spd.setRange(2, 20)
        s_spd.setValue(int(self.core.cfg["ripple_speed"] * 100))
        s_spd.valueChanged.connect(self.set_spd)
        l2.addWidget(s_spd)

        self.lbl_drp = QtWidgets.QLabel(f"Max Einschläge: {self.core.cfg['max_drops']}")
        l2.addWidget(self.lbl_drp)
        s_drp = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_drp.setRange(1, 8)
        s_drp.setValue(self.core.cfg["max_drops"])
        s_drp.valueChanged.connect(self.set_drp)
        l2.addWidget(s_drp)

        l2.addWidget(QtWidgets.QLabel("Reaktions-Modus:"))
        self.combo_mode = QtWidgets.QComboBox()
        self.combo_mode.addItems(["Ripple", "Spikes", "Pulse", "Vortex"])
        self.combo_mode.setCurrentText(self.core.cfg["active_mode"])
        self.combo_mode.currentTextChanged.connect(self.set_mode)
        l2.addWidget(self.combo_mode)

        l2.addStretch()
        tabs.addTab(t2, "Audio")

        # Tab 3: System-Telemetrie
        t3 = QtWidgets.QWidget()
        l3 = QtWidgets.QVBoxLayout(t3)
        l3.setContentsMargins(10, 10, 10, 10)
        l3.setSpacing(8)

        self.lbl_cpu = QtWidgets.QLabel(f"CPU-Turbulenz: {self.core.cfg['cpu_turbulence']:.1f}x")
        l3.addWidget(self.lbl_cpu)
        s_cpu = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_cpu.setRange(0, 40)
        s_cpu.setValue(int(self.core.cfg["cpu_turbulence"] * 10))
        s_cpu.valueChanged.connect(self.set_cpu)
        l3.addWidget(s_cpu)

        self.lbl_rot = QtWidgets.QLabel(f"Rotations-Tempo: {self.core.cfg['rot_speed']:.1f}x")
        l3.addWidget(self.lbl_rot)
        s_rot = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_rot.setRange(1, 30)
        s_rot.setValue(int(self.core.cfg["rot_speed"] * 10))
        s_rot.valueChanged.connect(self.set_rot)
        l3.addWidget(s_rot)

        self.lbl_ram = QtWidgets.QLabel(f"RAM-Dichte-Kopplung: {self.core.cfg['ram_coupling']:.1f}x")
        l3.addWidget(self.lbl_ram)
        s_ram = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        s_ram.setRange(0, 30)
        s_ram.setValue(int(self.core.cfg["ram_coupling"] * 10))
        s_ram.valueChanged.connect(self.set_ram)
        l3.addWidget(s_ram)

        self.btn_roam = QtWidgets.QPushButton(f"Auto-Wandern (Desktop): {'AN' if self.core.cfg['roam_enabled'] else 'AUS'}")
        self.btn_roam.clicked.connect(self.toggle_roam)
        l3.addWidget(self.btn_roam)

        l3.addStretch()
        tabs.addTab(t3, "System")

        # Tab 4: Launcher Slots
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        t4 = QtWidgets.QWidget()
        l4 = QtWidgets.QVBoxLayout(t4)
        l4.setContentsMargins(10, 10, 10, 10)
        l4.setSpacing(10)

        self.slot_edits = []
        for i, sl in enumerate(self.core.cfg["slots"]):
            box = QtWidgets.QGroupBox(f"{sl['name']}")
            box_layout = QtWidgets.QVBoxLayout(box)
            box_layout.setContentsMargins(8, 12, 8, 8)
            box_layout.setSpacing(6)

            h_layout = QtWidgets.QHBoxLayout()
            h_layout.setSpacing(6)

            edt = QtWidgets.QLineEdit(sl["path"])
            edt.setReadOnly(sl.get("locked", False))
            h_layout.addWidget(edt)

            if not sl.get("locked", False):
                btn_brw = QtWidgets.QToolButton()
                btn_brw.setText("📁")
                btn_brw.setFixedSize(30, 26)
                btn_brw.clicked.connect(lambda ch, idx=i, ed=edt: self.browse_slot(idx, ed))
                h_layout.addWidget(btn_brw)

            box_layout.addLayout(h_layout)
            l4.addWidget(box)
            self.slot_edits.append(edt)

        btn_save_slots = QtWidgets.QPushButton("Pfade speichern & aktualisieren")
        btn_save_slots.clicked.connect(self.save_slots)
        l4.addWidget(btn_save_slots)
        l4.addStretch()

        scroll_area.setWidget(t4)
        tabs.addTab(scroll_area, "Launcher")

        # Tab 5: Hotkey & Anleitung
        t5 = QtWidgets.QWidget()
        l5 = QtWidgets.QVBoxLayout(t5)
        l5.setContentsMargins(10, 10, 10, 10)
        l5.setSpacing(8)

        l5.addWidget(QtWidgets.QLabel("<b>Systemweiter KDE-Hotkey:</b>"))
        h_box = QtWidgets.QHBoxLayout()
        self.edt_hotkey = QtWidgets.QLineEdit(self.core.cfg.get("hotkey", "Ctrl+Shift+J"))
        h_box.addWidget(self.edt_hotkey)
        btn_set_hotkey = QtWidgets.QPushButton("Aktivieren")
        btn_set_hotkey.setFixedWidth(90)
        btn_set_hotkey.clicked.connect(self.apply_hotkey)
        h_box.addWidget(btn_set_hotkey)
        l5.addLayout(h_box)

        l5.addWidget(QtWidgets.QLabel("<b>Steuerung & Tastenkürzel:</b>"))
        txt_manual = QtWidgets.QTextEdit()
        txt_manual.setReadOnly(True)
        txt_manual.setHtml("""
        <p><b>Modus-Trennung:</b></p>
        <ul>
            <li><b>Taste E:</b> Schaltet den <i>Bearbeitungsmodus</i> inkl. Zahnrad AN/AUS.</li>
            <li><b>Bearbeitungsmodus AN:</b> Zeigt Rahmen. Klick in die Fläche verschiebt Fenster, Ziehen an den Ecken skaliert.</li>
            <li><b>Bearbeitungsmodus AUS:</b> Fenster fixiert. Kugel-Steuerung aktiv:</li>
        </ul>
        <p><b>Kugel-Interaktion (Fixierter Zustand):</b></p>
        <ul>
            <li><b>Hover-Magnet:</b> Maus in Knotennähe bremst die Rotation dynamisch auf 15 % ab.</li>
            <li><b>Hover-Blasen:</b> Maus direkt über einem Knoten lässt 4 Sub-Orbit-Blasen aufsteigen.</li>
            <li><b>Linksklick halten & Ziehen:</b> Kugel frei im 3D-Raum drehen (Trackball).</li>
            <li><b>Mausrad:</b> Kugel stufenlos skalieren (Zoom).</li>
            <li><b>Doppelklick / Leertaste:</b> Snap-to-Front (richtet die 4 Slots frontal aus).</li>
            <li><b>Klick auf Knoten:</b> Öffnet Ordner oder startet Tool.</li>
            <li><b>Taste C:</b> Öffnet/Schließt dieses Einstellungsmenü jederzeit.</li>
        </ul>
        """)
        l5.addWidget(txt_manual)
        tabs.addTab(t5, "Anleitung")

    def toggle_edit(self):
        self.core.cfg["edit_mode"] = not self.core.cfg["edit_mode"]
        self.btn_edit.setText(f"Bearbeitungsmodus: {'AN' if self.core.cfg['edit_mode'] else 'AUS'}")
        self.core.update_gear_visibility()
        self.core.update()
        save_config(self.core.cfg)

    def cycle_color(self):
        self.core.cfg["color_flow"] = False
        self.btn_flow.setText("Farb-Flow: AUS")
        self.core.cfg["color_idx"] = (self.core.cfg["color_idx"] + 1) % len(self.core.colors)
        save_config(self.core.cfg)

    def toggle_flow(self):
        self.core.cfg["color_flow"] = not self.core.cfg["color_flow"]
        self.btn_flow.setText(f"Farb-Flow: {'AN' if self.core.cfg['color_flow'] else 'AUS'}")
        save_config(self.core.cfg)

    def set_den(self, val):
        self.core.cfg["particle_count"] = val
        self.lbl_den.setText(f"Partikeldichte: {val}")
        save_config(self.core.cfg)

    def set_sz(self, val):
        self.core.cfg["base_particle_size"] = val / 10.0
        self.lbl_sz.setText(f"Partikelgröße: {self.core.cfg['base_particle_size']:.1f}")
        save_config(self.core.cfg)

    def set_scale(self, val):
        self.core.cfg["sphere_scale"] = val / 100.0
        self.lbl_scale.setText(f"Sphären-Skalierung: {self.core.cfg['sphere_scale']:.2f}")
        save_config(self.core.cfg)

    def toggle_dir(self):
        self.core.cfg["wave_direction"] *= -1
        self.btn_dir.setText(f"Wellen: {'AUSSEN' if self.core.cfg['wave_direction'] == 1 else 'INNEN'}")
        save_config(self.core.cfg)

    def set_thr(self, val):
        self.core.cfg["trigger_thresh"] = val / 100.0
        self.lbl_thr.setText(f"Auslöse-Schwelle: {self.core.cfg['trigger_thresh']:.2f}")
        save_config(self.core.cfg)

    def set_rip(self, val):
        self.core.cfg["ripple_strength"] = val / 10.0
        self.lbl_rip.setText(f"Wellen-Stärke: {self.core.cfg['ripple_strength']:.1f}x")
        save_config(self.core.cfg)

    def set_ar(self, val):
        self.core.cfg["ripple_area"] = val / 100.0
        self.lbl_area.setText(f"Wellen-Breite: {self.core.cfg['ripple_area']:.2f}")
        save_config(self.core.cfg)

    def set_spd(self, val):
        self.core.cfg["ripple_speed"] = val / 100.0
        self.lbl_spd.setText(f"Ausbreitungs-Tempo: {self.core.cfg['ripple_speed']:.2f}")
        save_config(self.core.cfg)

    def set_drp(self, val):
        self.core.cfg["max_drops"] = val
        self.lbl_drp.setText(f"Max Einschläge: {val}")
        save_config(self.core.cfg)

    def set_mode(self, txt):
        self.core.cfg["active_mode"] = txt
        save_config(self.core.cfg)

    def set_cpu(self, val):
        self.core.cfg["cpu_turbulence"] = val / 10.0
        self.lbl_cpu.setText(f"CPU-Turbulenz: {self.core.cfg['cpu_turbulence']:.1f}x")
        save_config(self.core.cfg)

    def set_rot(self, val):
        self.core.cfg["rot_speed"] = val / 10.0
        self.lbl_rot.setText(f"Rotations-Tempo: {self.core.cfg['rot_speed']:.1f}x")
        save_config(self.core.cfg)

    def set_ram(self, val):
        self.core.cfg["ram_coupling"] = val / 10.0
        self.lbl_ram.setText(f"RAM-Dichte-Kopplung: {self.core.cfg['ram_coupling']:.1f}x")
        save_config(self.core.cfg)

    def toggle_roam(self):
        self.core.cfg["roam_enabled"] = not self.core.cfg["roam_enabled"]
        self.btn_roam.setText(f"Auto-Wandern (Desktop): {'AN' if self.core.cfg['roam_enabled'] else 'AUS'}")
        save_config(self.core.cfg)

    def browse_slot(self, idx, line_edit):
        p = QtWidgets.QFileDialog.getExistingDirectory(self, "Ordner auswählen", line_edit.text())
        if p:
            line_edit.setText(p)

    def save_slots(self):
        for i, edt in enumerate(self.slot_edits):
            self.core.cfg["slots"][i]["path"] = edt.text().strip()
        save_config(self.core.cfg)
        self.core.init_nodes()
        QtWidgets.QMessageBox.information(self, "Jarvis Core", "Pfade erfolgreich aktualisiert!")

    def apply_hotkey(self):
        hk = self.edt_hotkey.text().strip()
        if not hk:
            return
        self.core.cfg["hotkey"] = hk
        save_config(self.core.cfg)
        cfg_file = Path.home() / ".config" / "kglobalshortcutsrc"
        if cfg_file.exists():
            try:
                subprocess.run(
                    ["sed", "-i", f"/_launch=/s/=.*/={hk},none,Jarvis Spatial Core/", str(cfg_file)],
                    check=False
                )
                subprocess.run(["qdbus", "org.kde.kglobalaccel", "/kglobalaccel", "reloadConfig"], check=False)
                QtWidgets.QMessageBox.information(self, "Jarvis Core", f"Hotkey {hk} erfolgreich aktiviert!")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Fehler", f"Konnte Hotkey nicht setzen: {e}")

class JarvisOverlayWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()

        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.SubWindow |
            QtCore.Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setGeometry(250, 250, 560, 560)
        self.setMinimumSize(220, 220)
        self.setMouseTracking(True)

        self.colors = [
            QtGui.QColor(0, 240, 255), QtGui.QColor(255, 30, 60),
            QtGui.QColor(255, 140, 0), QtGui.QColor(0, 255, 150),
            QtGui.QColor(190, 50, 255)
        ]

        self.hovered_node = None
        self.proximity_factor = 1.0
        self.rot_y = 0.0
        self.rot_x = 0.0
        self.rot_vel_y = 0.0
        self.rot_vel_x = 0.0
        self.time_val = 0.0
        self.hue_cycle = 0.55
        self.roam_vx = 1.6
        self.roam_vy = 1.2

        self.resizing_edge = None
        self.drag_start_cursor = QtCore.QPoint()
        self.drag_start_pos = QtCore.QPoint()
        self.drag_start_size = QtCore.QSize()
        self.trackball_active = False

        self.particles = [Particle() for _ in range(3000)]
        self.ripples = []
        self.last_beat_trigger = 0.0
        self.bass = self.mids = self.highs = self.raw_rms = self.audio_smooth = 0.0
        self.cpu = self.ram = 0.0

        self.init_nodes()
        self.init_gear_button()
        self.deck = ControlDeckWindow(self)
        self.update_gear_visibility()
        self.lower()

        self.worker = TelemetryWorker()
        self.worker.stats_updated.connect(self.on_telemetry)
        self.worker.start()

        self.audio = AudioMonitor()
        self.audio.fft_updated.connect(self.on_fft)
        self.audio.start()

        self.render_timer = QtCore.QTimer(self)
        self.render_timer.timeout.connect(self.tick)
        self.render_timer.start(16)

    def init_nodes(self):
        self.nodes = [
            CommandNode(0, self.cfg["slots"][0]["name"], self.cfg["slots"][0]["path"], "folder", 0.0, 0.0),
            CommandNode(1, self.cfg["slots"][1]["name"], self.cfg["slots"][1]["path"], "folder", 0.85, math.pi * 0.75),
            CommandNode(2, self.cfg["slots"][2]["name"], self.cfg["slots"][2]["path"], "tool", 0.85, -math.pi * 0.75),
            CommandNode(3, self.cfg["slots"][3]["name"], self.cfg["slots"][3]["path"], "folder", 1.25, math.pi * 0.1)
        ]

    def init_gear_button(self):
        self.btn_gear = QtWidgets.QToolButton(self)
        self.btn_gear.setText("⚙")
        self.btn_gear.setStyleSheet("""
            QToolButton {
                color: #00f0ff; background: rgba(10, 20, 30, 220);
                border: 1px solid #00f0ff; border-radius: 4px; font-size: 15px; padding: 2px;
            }
            QToolButton:hover { background: #00f0ff; color: #000000; }
        """)
        self.btn_gear.setFixedSize(28, 28)
        self.btn_gear.move(12, 12)
        self.btn_gear.clicked.connect(self.toggle_control_deck)

    def update_gear_visibility(self):
        show = self.cfg["edit_mode"] or self.deck.isVisible()
        self.btn_gear.setVisible(show)

    def toggle_control_deck(self):
        if self.deck.isVisible():
            self.deck.hide()
            self.update_gear_visibility()
        else:
            geo = self.geometry()
            scr = QtGui.QGuiApplication.primaryScreen().geometry()
            x = geo.right() + 25
            if x + self.deck.width() > scr.width():
                x = geo.left() - self.deck.width() - 25
            y = max(40, geo.top())
            self.deck.move(max(10, x), y)
            self.deck.show()
            self.update_gear_visibility()

    def snap_to_front(self):
        self.rot_y = 0.0
        self.rot_x = 0.0
        self.rot_vel_y = 0.0
        self.rot_vel_x = 0.0

    @QtCore.pyqtSlot(float, float)
    def on_telemetry(self, cpu, ram):
        self.cpu = cpu
        self.ram = ram

    @QtCore.pyqtSlot(float, float, float, float)
    def on_fft(self, bass, mids, highs, raw_rms):
        self.bass = bass
        self.mids = mids
        self.highs = highs
        self.raw_rms = raw_rms

    def tick(self):
        self.time_val += 0.03
        eff = self.bass * 0.65 + self.highs * 0.35
        if eff > self.audio_smooth:
            self.audio_smooth = eff
        else:
            self.audio_smooth += (eff - self.audio_smooth) * 0.22

        now = self.time_val
        if self.audio_smooth > self.cfg["trigger_thresh"] and len(self.ripples) < self.cfg["max_drops"]:
            if (now - self.last_beat_trigger) > (0.16 / self.cfg["max_drops"]):
                self.last_beat_trigger = now
                self.ripples.append(RippleDrop(
                    self.audio_smooth * 18.0 * self.cfg["ripple_strength"],
                    self.cfg["ripple_speed"],
                    self.cfg["ripple_area"],
                    self.cfg["wave_direction"]
                ))

        self.ripples = [r for r in self.ripples if r.advance()]

        if self.cfg["color_flow"]:
            self.hue_cycle = (self.hue_cycle + 0.001 + (self.audio_smooth * 0.007)) % 1.0

        for n in self.nodes:
            if n == self.hovered_node:
                n.bubble_progress = min(1.0, n.bubble_progress + 0.12)
            else:
                n.bubble_progress = max(0.0, n.bubble_progress - 0.10)

        if self.cfg["roam_enabled"] and not self.cfg["edit_mode"] and not self.trackball_active and self.audio_smooth > 0.04:
            screen = QtGui.QGuiApplication.primaryScreen().geometry()
            cur = self.pos()
            spd = 1.0 + (self.audio_smooth * 3.5)
            nx = cur.x() + int(self.roam_vx * spd)
            ny = cur.y() + int(self.roam_vy * spd)
            if nx <= 0 or nx + self.width() >= screen.width():
                self.roam_vx *= -1
                nx = max(0, min(nx, screen.width() - self.width()))
            if ny <= 0 or ny + self.height() >= screen.height():
                self.roam_vy *= -1
                ny = max(0, min(ny, screen.height() - self.height()))
            self.move(nx, ny)

        if self.trackball_active:
            self.rot_y += self.rot_vel_y
            self.rot_x += self.rot_vel_x
            self.rot_vel_y *= 0.92
            self.rot_vel_x *= 0.92
        else:
            spd_mul = self.proximity_factor * self.cfg["rot_speed"]
            self.rot_y += (0.008 + (self.cpu / 100.0 * 0.015) + (self.audio_smooth * 0.03)) * spd_mul
            self.rot_x += (0.003) * spd_mul

        self.update()

    def get_corner(self, pos):
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        hs = 28
        if not self.cfg["edit_mode"]:
            return None
        if x <= hs and y <= hs: return "TL"
        elif x >= w - hs and y <= hs: return "TR"
        elif x <= hs and y >= h - hs: return "BL"
        elif x >= w - hs and y >= h - hs: return "BR"
        return None

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.snap_to_front()
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self.btn_gear.isVisible() and self.btn_gear.geometry().contains(event.pos()):
                return

            if self.cfg["edit_mode"]:
                corner = self.get_corner(event.pos())
                if corner:
                    self.resizing_edge = corner
                    self.drag_start_cursor = event.globalPosition().toPoint()
                    self.drag_start_pos = self.pos()
                    self.drag_start_size = self.size()
                    event.accept()
                else:
                    win = self.windowHandle()
                    if win: win.startSystemMove()
                    event.accept()
                return

            if self.hovered_node:
                p = self.hovered_node.path
                if os.path.exists(p) or shutil.which(p):
                    subprocess.Popen(["xdg-open" if os.path.exists(p) else p, p])
                return

            self.trackball_active = True
            self.drag_start_cursor = event.globalPosition().toPoint()
            self.rot_vel_y = 0.0
            self.rot_vel_x = 0.0
            event.accept()

    def mouseMoveEvent(self, event):
        m_pos = event.pos()
        min_dist = 9999.0
        found_hover = None

        for n in self.nodes:
            if n.proj_z > -50.0:
                dist = math.hypot(m_pos.x() - n.proj_x, m_pos.y() - n.proj_y)
                if dist < min_dist:
                    min_dist = dist
                if dist < 24.0:
                    found_hover = n

        self.hovered_node = found_hover

        if min_dist < 85.0:
            norm_dist = max(0.0, (min_dist - 20.0) / 65.0)
            self.proximity_factor = 0.15 + (norm_dist * 0.85)
        else:
            self.proximity_factor = 1.0

        if self.trackball_active:
            delta = event.globalPosition().toPoint() - self.drag_start_cursor
            self.rot_vel_y = delta.x() * 0.008
            self.rot_vel_x = -delta.y() * 0.008
            self.rot_y += self.rot_vel_y
            self.rot_x += self.rot_vel_x
            self.drag_start_cursor = event.globalPosition().toPoint()
            return

        if self.resizing_edge:
            delta = event.globalPosition().toPoint() - self.drag_start_cursor
            orig_w = self.drag_start_size.width()
            orig_h = self.drag_start_size.height()
            orig_x = self.drag_start_pos.x()
            orig_y = self.drag_start_pos.y()

            if self.resizing_edge == "BR":
                side = max(self.minimumWidth(), orig_w + max(delta.x(), delta.y()))
                self.resize(side, side)
            elif self.resizing_edge == "TL":
                side = max(self.minimumWidth(), orig_w - min(delta.x(), delta.y()))
                self.setGeometry(orig_x + (orig_w - side), orig_y + (orig_h - side), side, side)
            elif self.resizing_edge == "TR":
                side = max(self.minimumWidth(), orig_w + delta.x(), orig_h - delta.y())
                self.setGeometry(orig_x, orig_y + (orig_h - side), side, side)
            elif self.resizing_edge == "BL":
                side = max(self.minimumWidth(), orig_w - delta.x(), orig_h + delta.y())
                self.setGeometry(orig_x + (orig_w - side), orig_y, side, side)
            return

        if self.cfg["edit_mode"]:
            c = self.get_corner(m_pos)
            if c in ("TL", "BR"): self.setCursor(QtCore.Qt.CursorShape.SizeFDiagCursor)
            elif c in ("TR", "BL"): self.setCursor(QtCore.Qt.CursorShape.SizeBDiagCursor)
            else: self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        else:
            if self.hovered_node: self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            else: self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event):
        self.resizing_edge = None
        self.trackball_active = False
        self.lower()

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        new_sc = max(0.18, min(0.48, self.cfg["sphere_scale"] + delta * 0.02))
        self.cfg["sphere_scale"] = new_sc
        self.deck.lbl_scale.setText(f"Sphären-Skalierung: {self.cfg['sphere_scale']:.2f}")
        save_config(self.cfg)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_E:
            self.cfg["edit_mode"] = not self.cfg["edit_mode"]
            self.deck.btn_edit.setText(f"Bearbeitungsmodus: {'AN' if self.cfg['edit_mode'] else 'AUS'}")
            self.update_gear_visibility()
            self.update()
            save_config(self.cfg)
        elif event.key() == QtCore.Qt.Key.Key_C:
            self.toggle_control_deck()
        elif event.key() in (QtCore.Qt.Key.Key_Space, QtCore.Qt.Key.Key_Return):
            self.snap_to_front()
        super().keyPressEvent(event)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        base_r = min(w, h) * self.cfg["sphere_scale"]

        if self.cfg["color_flow"]:
            rgb = colorsys.hsv_to_rgb(self.hue_cycle, 0.92, 1.0)
            col = QtGui.QColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
        else:
            col = self.colors[self.cfg["color_idx"]]

        p.setPen(QtCore.Qt.PenStyle.NoPen)
        p.setBrush(QtGui.QColor(0, 0, 0, 1))
        p.drawRect(0, 0, w, h)

        if self.cfg["edit_mode"]:
            pen = QtGui.QPen(QtGui.QColor(col.red(), col.green(), col.blue(), 140), 1.5, QtCore.Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawRect(2, 2, w - 4, h - 4)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(col.red(), col.green(), col.blue(), 230))
            hs = 12
            p.drawRect(2, 2, hs, hs); p.drawRect(w - hs - 2, 2, hs, hs)
            p.drawRect(2, h - hs - 2, hs, hs); p.drawRect(w - hs - 2, h - hs - 2, hs, hs)

        cos_y = math.cos(self.rot_y); sin_y = math.sin(self.rot_y)
        cos_x = math.cos(self.rot_x); sin_x = math.sin(self.rot_x)
        fov = 340.0

        ram_bonus = int((self.ram / 100.0) * 400 * self.cfg["ram_coupling"])
        active_count = min(len(self.particles), self.cfg["particle_count"] + ram_bonus)
        pts = self.particles[:active_count]

        for pt in pts:
            disp = 0.0
            if len(self.ripples) > 0:
                for r in self.ripples:
                    dot = pt.nx * r.center_nx + pt.ny * r.center_ny + pt.nz * r.center_nz
                    arc = math.acos(max(-1.0, min(1.0, dot)))
                    delta = arc - r.radius
                    if abs(delta) < r.area_scale:
                        disp += math.cos(delta * (math.pi / r.area_scale)) * r.strength * r.direction

            final_r = max(8.0, base_r + disp)
            lx = final_r * pt.nx; ly = final_r * pt.ny; lz = final_r * pt.nz
            x1 = lx * cos_y + lz * sin_y; z1 = -lx * sin_y + lz * cos_y
            pt.x = x1; pt.y = ly * cos_x - z1 * sin_x; pt.z = ly * sin_x + z1 * cos_x

        pts.sort(key=lambda item: item.z)
        p.setPen(QtCore.Qt.PenStyle.NoPen)

        for pt in pts:
            dist = fov / (fov + pt.z + 180.0)
            px = cx + (pt.x * dist)
            py = cy + (pt.y * dist)
            alpha = int(max(25, min(255, (pt.z + base_r) / (2.0 * base_r) * 255)))
            sz = max(0.5, self.cfg["base_particle_size"] * dist * pt.size_mod * pt.cluster_weight * (w / 560.0))
            p.setBrush(QtGui.QColor(col.red(), col.green(), col.blue(), int(alpha * 0.90)))
            p.drawEllipse(QtCore.QPointF(px, py), sz, sz)

        for n in self.nodes:
            lx = (base_r + 14.0) * n.nx; ly = (base_r + 14.0) * n.ny; lz = (base_r + 14.0) * n.nz
            x1 = lx * cos_y + lz * sin_y; z1 = -lx * sin_y + lz * cos_y
            n.proj_z = ly * sin_x + z1 * cos_x
            dist = fov / (fov + n.proj_z + 180.0)
            n.proj_x = cx + (x1 * dist)
            n.proj_y = cy + ((ly * cos_x - z1 * sin_x) * dist)

            if n.proj_z > -50.0:
                is_hov = (n == self.hovered_node)
                node_sz = 10.0 if is_hov else 6.0

                p.setPen(QtGui.QPen(QtGui.QColor(0, 240, 255, 240), 1.5))
                p.setBrush(QtGui.QColor(255 if is_hov else col.red(), 255 if is_hov else col.green(), 255 if is_hov else col.blue(), 240))
                p.drawEllipse(QtCore.QPointF(n.proj_x, n.proj_y), node_sz, node_sz)

                if n.bubble_progress > 0.01:
                    prog = n.bubble_progress
                    orbit_r = 28.0 * prog
                    bubble_count = 4

                    for b_idx in range(bubble_count):
                        angle = (self.time_val * 1.5) + (b_idx * (2.0 * math.pi / bubble_count))
                        bx = n.proj_x + math.cos(angle) * orbit_r
                        by = n.proj_y + math.sin(angle) * orbit_r
                        bsz = (4.0 + math.sin(self.time_val * 4.0 + b_idx) * 1.0) * prog

                        p.setPen(QtGui.QPen(QtGui.QColor(0, 240, 255, int(110 * prog)), 1.0, QtCore.Qt.PenStyle.DotLine))
                        p.drawLine(QtCore.QPointF(n.proj_x, n.proj_y), QtCore.QPointF(bx, by))

                        p.setPen(QtGui.QPen(QtGui.QColor(0, 240, 255, int(200 * prog)), 1.0))
                        p.setBrush(QtGui.QColor(col.red(), col.green(), col.blue(), int(160 * prog)))
                        p.drawEllipse(QtCore.QPointF(bx, by), bsz, bsz)

                if is_hov:
                    hud_x = n.proj_x + 38
                    hud_y = n.proj_y - 38
                    p.setPen(QtGui.QPen(QtGui.QColor(0, 240, 255, 220), 1.2))
                    p.drawLine(QtCore.QPointF(n.proj_x, n.proj_y), QtCore.QPointF(hud_x, hud_y))
                    p.drawLine(QtCore.QPointF(hud_x, hud_y), QtCore.QPointF(hud_x + 135, hud_y))

                    p.setBrush(QtGui.QColor(8, 16, 26, 245))
                    p.drawRect(int(hud_x), int(hud_y - 24), 170, 50)
                    p.setPen(QtGui.QColor(0, 240, 255))
                    font = p.font(); font.setBold(True); font.setPixelSize(10); p.setFont(font)
                    p.drawText(int(hud_x + 6), int(hud_y - 8), n.label)
                    font.setBold(False); font.setPixelSize(9); p.setFont(font)
                    p.setPen(QtGui.QColor(180, 220, 240))
                    p.drawText(int(hud_x + 6), int(hud_y + 8), f"Typ: {n.n_type.upper()}")
                    p.drawText(int(hud_x + 6), int(hud_y + 20), "[Klick]: Starten / Öffnen")

    def closeEvent(self, event):
        self.worker.stop()
        self.audio.stop()
        self.deck.close()
        event.accept()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = JarvisOverlayWidget()
    widget.show()
    widget.lower()
    sys.exit(app.exec())
