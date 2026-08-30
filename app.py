# Copyright (C) 2026 szabiz - Soli Deo Gloria
#
# Pop Filter Pro Application
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
app.py - INTELLIGENS POP-FILTER GUI (v2.0 - Saját Natív Canvas Motor & Cubic Spline Görbe)
Copyright (c) szabiz 2026 - Soli Deo Gloria
"""

import sys
import os
import json
import threading
import queue
import time
import copy
import multiprocessing
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np

import sounddevice as sd
import pop_core as core

VERSION = "2.00"

def resource_path(relative_path):
    """ Megkeresi a fájlt akár forrásból, akár PyInstaller .exe-ből fut a program """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

LANG = {
    'HU': {
        'title': f"Pop Filter Pro v{VERSION} - Intelligens pop-zaj eltávolító Engine",
        'open': "Fájl megnyitása...",
        'orig': "▶ Eredeti",
        'filtered': "▶ Szűrt előnézet",
        'rendering': "⏳ Feldolgozás...",
        'delta_off': "🎧 Delta (Csak a kivágott zaj)",
        'delta_on': "🎧 DELTA MÓD (Aktív)",
        'stop': "■ Stop",
        'export_labels': "Audacity Labels...",
        'reset_zoom': "🔍 Nézet visszaállítása",
        'auto_tune': "⚡ Gyári alapbeállítás",
        'save_preset': "💾 Profil mentése",
        'load_preset': "📂 Profil betöltése",
        'about': "ℹ️ Névjegy",
        'save_wav': "Szűrt mentése...",
        'no_file': "Nincs fájl betöltve",
        'settings_head': "Pop-detektálás beállításai",
        'lbl_low': "Sáv alsó határa (Hz)",
        'lbl_high': "Sáv felső határa (Hz)",
        'lbl_thresh': "Érzékenység / küszöb (dB)",
        'lbl_max_dur': "Max. pop hossz (ms)",
        'lbl_max_red': "Max. csillapítás (dB)",
        'live_check': "Élő frissítés mozgatáskor",
        'help_text': "💡 Kattints egy popra az egyedi szerkesztéshez (#1, #2...)\n💡 Kattints a skálán a lejátszófej pozicionálásához.\n💡 Görgess az eltoláshoz, Ctrl + Görgetés a nagyításhoz.",
        'detected_text': "{count} pop-szakasz észlelve, ~{dur:.2f} s érintett.",
        'plot_title': "{path} - Piros = Globális | Narancs = Egyedi (#1, #2...)",
        'time_axis': "Idő (s)",
        'amp_axis': "Amplitúdó",
        'lang_btn': "🇬🇧 English",
        'prog_title': "Feldolgozás...",
        'btn_global_mode': "🌐 Vissza a globális módba",
        'btn_clear_reg': "❌ Egyedi beállítás törlése erről",
    },
    'EN': {
        'title': f"Pop Filter Pro v{VERSION} - Intelligent De-Plosive Engine",
        'open': "Open File...",
        'orig': "▶ Original",
        'filtered': "▶ Filtered Preview",
        'rendering': "⏳ Processing...",
        'delta_off': "🎧 Delta (Noise Only)",
        'delta_on': "🎧 DELTA MODE (Active)",
        'stop': "■ Stop",
        'export_labels': "Audacity Labels...",
        'reset_zoom': "🔍 Reset View",
        'auto_tune': "⚡ Default Preset",
        'save_preset': "💾 Save Preset",
        'load_preset': "📂 Load Preset",
        'about': "ℹ️ About",
        'save_wav': "Save Filtered...",
        'no_file': "No file loaded",
        'settings_head': "Pop Detection Settings",
        'lbl_low': "Low Frequency Cutoff (Hz)",
        'lbl_high': "High Frequency Cutoff (Hz)",
        'lbl_thresh': "Sensitivity / Threshold (dB)",
        'lbl_max_dur': "Max Pop Duration (ms)",
        'lbl_max_red': "Max Attenuation (dB)",
        'live_check': "Live update on slider drag",
        'help_text': "💡 Click a pop to custom edit (#1, #2...)\n💡 Click canvas to set playhead position.\n💡 Scroll to pan, Ctrl + Scroll to zoom.",
        'detected_text': "{count} pop segments detected, ~{dur:.2f} s affected.",
        'plot_title': "{path} - Red = Global | Orange = Custom (#1, #2...)",
        'time_axis': "Time (s)",
        'amp_axis': "Amplitude",
        'lang_btn': "🇭🇺 Magyar",
        'prog_title': "Processing...",
        'btn_global_mode': "🌐 Back to Global Mode",
        'btn_clear_reg': "❌ Clear Custom for this Pop",
    }
}


class ProgressDialog(tk.Toplevel):
    def __init__(self, parent, title="Feldolgozás..."):
        super().__init__(parent)
        self.title(title)
        self.geometry("420x130")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 210
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 65
        self.geometry(f"+{x}+{y}")

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        self.lbl_status = ttk.Label(frame, text="Folyamat indítása...", font=("Segoe UI", 9, "bold"))
        self.lbl_status.pack(anchor=tk.W, pady=(0, 8))

        self.progress = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=380, mode='determinate')
        self.progress.pack(fill=tk.X, pady=5)

        self.lbl_pct = ttk.Label(frame, text="0%", font=("Segoe UI", 8))
        self.lbl_pct.pack(anchor=tk.E)

    def update_progress(self, percent, msg):
        self.progress['value'] = percent
        self.lbl_status.config(text=msg)
        self.lbl_pct.config(text=f"{int(percent)}%")
        self.update_idletasks()


class NativeWaveformCanvas(tk.Canvas):
    """ Saját natív Tkinter Canvas hullámrajzoló motor (Min-Max Envelope + Cubic Spline Görbe) """
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, bg="#ffffff", highlightthickness=0, bd=0, **kwargs)
        self.app = app
        self.audio = None
        self.view_start = 0.0
        self.view_end = 1.0
        self.playhead_t = 0.0

        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<MouseWheel>", self._on_scroll)
        self.bind("<Button-4>", lambda e: self._on_scroll_linux(e, -1))
        self.bind("<Button-5>", lambda e: self._on_scroll_linux(e, 1))

    def load_audio(self, audio):
        self.audio = audio
        self.view_start = 0.0
        self.view_end = audio.duration_s
        self.redraw()

    def reset_zoom(self):
        if self.audio:
            self.view_start = 0.0
            self.view_end = self.audio.duration_s
            self.redraw()

    def redraw(self):
        self.delete("all")
        if self.audio is None or self.audio.samples is None:
            return

        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 10 or height <= 10:
            return

        ruler_h = 24
        wave_h = height - ruler_h
        mid_y = wave_h / 2.0
        scale_y = (wave_h / 2.0) * 0.85

        start_s = max(0.0, self.view_start)
        end_s = min(self.audio.duration_s, self.view_end)
        if end_s <= start_s:
            end_s = start_s + 0.01

        fs = self.audio.fs
        start_idx = int(start_s * fs)
        end_idx = int(end_s * fs)
        n_samples = end_idx - start_idx

        if n_samples <= 0:
            return

        # 1. POP KIJELÖLÉSEK KIRAJZOLÁSA (Háttér sávok)
        for s_t, e_t, _ in self.app.segments:
            if e_t < start_s or s_t > end_s:
                continue

            x1 = int((s_t - start_s) / (end_s - start_s) * width)
            x2 = int((e_t - start_s) / (end_s - start_s) * width)
            x1 = max(0, min(width, x1))
            x2 = max(0, min(width, x2))

            matched_reg = next((r for r in self.app.custom_regions if abs(r['start_t'] - s_t) <= self.app.REGION_MATCH_TOLERANCE_S), None)

            if matched_reg:
                reg_idx = self.app.custom_regions.index(matched_reg)
                self.create_rectangle(x1, 0, x2, wave_h, fill="#ffe0b2", outline="#f57c00", width=1)
                mid_x = (x1 + x2) / 2
                self.create_text(mid_x, 15, text=f"#{reg_idx+1}", fill="#e65100", font=("Segoe UI", 9, "bold"))
            else:
                self.create_rectangle(x1, 0, x2, wave_h, fill="#ffcdd2", outline="#e53935", width=1)

        # 2. HULLÁMFORMA KIRAJZOLÁSA
        sub_samples = self.audio.samples[start_idx:end_idx]

        # KÖZELNÉZET: Köbös (Cubic) Spline interpoláció a fűrészfogak ellen
        if 3 < n_samples < width * 2:
            try:
                from scipy.interpolate import interp1d
                x_raw = np.linspace(0, width, n_samples)
                x_dense = np.linspace(0, width, min(width * 2, n_samples * 6))
                f_interp = interp1d(x_raw, sub_samples, kind='cubic')
                y_dense = f_interp(x_dense)

                poly_pts = []
                for x_px, val in zip(x_dense, y_dense):
                    y_px = mid_y - (val * scale_y)
                    poly_pts.extend([x_px, y_px])
                
                self.create_line(*poly_pts, fill="#2b5cbe", width=1.8, smooth=True)
            except Exception:
                x_raw = np.linspace(0, width, n_samples)
                poly_pts = []
                for x_px, val in zip(x_raw, sub_samples):
                    y_px = mid_y - (val * scale_y)
                    poly_pts.extend([x_px, y_px])
                self.create_line(*poly_pts, fill="#2b5cbe", width=1.5)

        else:
            # TÁVOLI NÉZET: Pontos, pixelenkénti Min-Max Envelope (A teljes szélességet lefedi)
            indices = np.linspace(0, n_samples, width + 1, dtype=int)
            for x in range(width):
                idx_start = indices[x]
                idx_end = indices[x + 1]
                if idx_start >= idx_end:
                    continue
                
                chunk = sub_samples[idx_start:idx_end]
                y_min = mid_y - (np.min(chunk) * scale_y)
                y_max = mid_y - (np.max(chunk) * scale_y)
                self.create_line(x, y_min, x, y_max, fill="#2b5cbe", width=1)

        # Nullvonal
        self.create_line(0, mid_y, width, mid_y, fill="#d0d0d0", dash=(2, 2))

        # 3. LEJÁTSZÓFEJ
        if start_s <= self.playhead_t <= end_s:
            px_head = (self.playhead_t - start_s) / (end_s - start_s) * width
            self.create_line(px_head, 0, px_head, wave_h, fill="#000000", width=2, dash=(4, 2), tags="playhead")

        # 4. IDŐ-SKÁLA (Tengely az alján)
        self.create_rectangle(0, wave_h, width, height, fill="#f8f9fa", outline="#e0e0e0")
        span = end_s - start_s
        num_ticks = 8
        for i in range(num_ticks + 1):
            tx = (i / num_ticks) * width
            t_val = start_s + (i / num_ticks) * span
            t_str = self.app._format_time_axis(t_val, span)
            self.create_line(tx, wave_h, tx, wave_h + 5, fill="#888888")
            anchor = tk.W if i == 0 else (tk.E if i == num_ticks else tk.CENTER)
            self.create_text(tx, wave_h + 13, text=t_str, fill="#555555", font=("Segoe UI", 8), anchor=anchor)

    def update_playhead(self, playhead_t):
        self.playhead_t = playhead_t
        if self.audio is None:
            return

        width = self.winfo_width()
        height = self.winfo_height()
        ruler_h = 24
        wave_h = height - ruler_h

        start_s = self.view_start
        end_s = self.view_end

        self.delete("playhead")
        if start_s <= self.playhead_t <= end_s and end_s > start_s:
            px_head = (self.playhead_t - start_s) / (end_s - start_s) * width
            self.create_line(px_head, 0, px_head, wave_h, fill="#000000", width=2, dash=(4, 2), tags="playhead")

    def _on_click(self, event):
        if self.audio is None:
            return
        width = self.winfo_width()
        ruler_h = 24
        wave_h = self.winfo_height() - ruler_h
        if event.y > wave_h:
            return

        span = self.view_end - self.view_start
        click_t = self.view_start + (event.x / width) * span
        click_t = max(0.0, min(self.audio.duration_s, click_t))

        self.app._on_waveform_click(click_t)
        
    def _on_double_click(self, event):
        if self.audio is None:
            return
        width = self.winfo_width()
        ruler_h = 24
        wave_h = self.winfo_height() - ruler_h
        if event.y > wave_h:
            return

        span = self.view_end - self.view_start
        click_t = self.view_start + (event.x / width) * span
        click_t = max(0.0, min(self.audio.duration_s, click_t))

        self.app._on_waveform_double_click(click_t)    

    def _on_scroll(self, event):
        if self.audio is None:
            return
        width = self.winfo_width()
        if width <= 0:
            return

        is_ctrl = (event.state & 0x0004) != 0 or (event.state & 0x0001) != 0
        delta = event.delta
        if delta == 0:
            return
        direction = 1 if delta < 0 else -1

        self._zoom_or_pan(event.x, width, direction, is_ctrl)

    def _on_scroll_linux(self, event, direction):
        if self.audio is None:
            return
        width = self.winfo_width()
        is_ctrl = (event.state & 0x0004) != 0
        self._zoom_or_pan(event.x, width, direction, is_ctrl)

    def _zoom_or_pan(self, x_px, width, direction, is_ctrl):
        span = self.view_end - self.view_start
        total = self.audio.duration_s

        if is_ctrl:
            factor = 1.35 if direction > 0 else 1.0 / 1.35
            new_span = span * factor
            if new_span >= total:
                self.view_start = 0.0
                self.view_end = total
            else:
                rel = x_px / width
                mouse_t = self.view_start + rel * span
                new_start = mouse_t - new_span * rel
                new_end = new_start + new_span

                if new_start < 0:
                    new_start = 0.0
                    new_end = new_span
                if new_end > total:
                    new_end = total
                    new_start = max(0.0, total - new_span)

                self.view_start = new_start
                self.view_end = new_end
        else:
            shift = span * 0.15 * direction
            new_start = self.view_start + shift
            new_end = self.view_end + shift

            if new_start < 0:
                new_start = 0.0
                new_end = min(total, span)
            elif new_end > total:
                new_end = total
                new_start = max(0.0, total - span)

            self.view_start = new_start
            self.view_end = new_end

        self.redraw()


class PopFilterApp(tk.Tk):
    REGION_MATCH_TOLERANCE_S = 0.06

    def __init__(self):
        super().__init__()
        
        self._updating_ui = False

        icon_file = resource_path("icon.ico")
        if os.path.exists(icon_file):
            try:
                self.iconbitmap(icon_file)
            except Exception as e:
                print(f"Ikon betöltési hiba: {e}")

        self.cur_lang = 'HU'
        self.audio = None
        self.cache = None
        self.params = core.PopParams()
        self.analyses = None
        self.segments = []
        
        self.custom_regions = []
        self.selected_region_index = None

        self.clean_samples = None
        self._clean_samples_from_sample = None

        self.play_start_time = 0.0
        self.playback_active = False
        self.playback_job = None
        self.playback_started_monotonic = 0.0
        self.playback_duration = 0.0

        self._live_debounce_job = None
        self._region_save_job = None
        self.delta_mode = False
        self.task_queue = queue.Queue()

        self._build_ui()
        self._update_language_text()
        self.after(30, self._process_queue)
        self.after(50, self._prewarm_scipy)

    def _prewarm_scipy(self):
        def work():
            try:
                import scipy.signal
                from scipy.ndimage import median_filter
                from scipy.interpolate import interp1d
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _build_ui(self):
        self.geometry("1280x760")

        top_bar = ttk.Frame(self, padding=5)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        self.btn_open = ttk.Button(top_bar, command=self._open_file)
        self.btn_open.pack(side=tk.LEFT, padx=2)

        self.btn_orig = ttk.Button(top_bar, command=self._play_orig)
        self.btn_orig.pack(side=tk.LEFT, padx=2)

        self.btn_filtered = ttk.Button(top_bar, command=self._play_filtered)
        self.btn_filtered.pack(side=tk.LEFT, padx=2)

        self.btn_delta = tk.Button(top_bar, command=self._toggle_delta, bg="#e1e1e1", relief=tk.RAISED, bd=1)
        self.btn_delta.pack(side=tk.LEFT, padx=4)

        self.btn_stop = ttk.Button(top_bar, command=self._stop_audio)
        self.btn_stop.pack(side=tk.LEFT, padx=2)

        self.btn_export_labels = ttk.Button(top_bar, command=self._export_audacity_labels)
        self.btn_export_labels.pack(side=tk.LEFT, padx=4)

        self.btn_reset_zoom = ttk.Button(top_bar, command=self._reset_zoom)
        self.btn_reset_zoom.pack(side=tk.LEFT, padx=4)

        self.btn_lang = ttk.Button(top_bar, command=self._toggle_language)
        self.btn_lang.pack(side=tk.LEFT, padx=6)

        self.btn_about = ttk.Button(top_bar, command=self._show_about)
        self.btn_about.pack(side=tk.LEFT, padx=2)

        self.btn_save_wav = ttk.Button(top_bar, command=self._save_file)
        self.btn_save_wav.pack(side=tk.RIGHT, padx=2)

        info_bar = ttk.Frame(self, padding=(5, 0, 5, 5))
        info_bar.pack(side=tk.TOP, fill=tk.X)
        self.lbl_info = ttk.Label(info_bar, text="", font=("Segoe UI", 9, "italic"))
        self.lbl_info.pack(side=tk.LEFT)

        main_box = ttk.Frame(self)
        main_box.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        plot_frame = ttk.Frame(main_box)
        plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Saját natív Tkinter hullámrajzoló
        self.wave_canvas = NativeWaveformCanvas(plot_frame, self)
        self.wave_canvas.pack(fill=tk.BOTH, expand=True)

        side_panel = ttk.Frame(main_box, width=300, padding=10)
        side_panel.pack(side=tk.RIGHT, fill=tk.Y)

        self.lbl_settings_head = ttk.Label(side_panel, font=("Segoe UI", 11, "bold"))
        self.lbl_settings_head.pack(anchor=tk.W, pady=5)

        self.mode_frame = ttk.LabelFrame(side_panel, text="Mód / Mode", padding=6)
        self.mode_frame.pack(fill=tk.X, pady=(0, 6))

        self.btn_global_mode = ttk.Button(self.mode_frame, command=self._set_global_mode)
        self.btn_global_mode.pack(fill=tk.X, pady=2)

        self.btn_clear_reg = ttk.Button(self.mode_frame, command=self._clear_selected_region)
        self.btn_clear_reg.pack(fill=tk.X, pady=2)

        self.presets_frame = ttk.LabelFrame(side_panel, text="Presets", padding=6)
        self.presets_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_auto_tune = ttk.Button(self.presets_frame, command=self._auto_tune)
        self.btn_auto_tune.pack(fill=tk.X, pady=2)

        self.btn_load_preset = ttk.Button(self.presets_frame, command=self._load_preset)
        self.btn_load_preset.pack(fill=tk.X, pady=2)

        self.btn_save_preset = ttk.Button(self.presets_frame, command=self._save_preset)
        self.btn_save_preset.pack(fill=tk.X, pady=2)

        self.sl_low, self.lbl_low_title = self._add_slider(side_panel, 20, 150, 37)
        self.sl_high, self.lbl_high_title = self._add_slider(side_panel, 100, 400, 172)
        self.sl_thresh, self.lbl_thresh_title = self._add_slider(side_panel, 1, 20, 13)
        self.sl_max_dur, self.lbl_max_dur_title = self._add_slider(side_panel, 50, 500, 180)
        self.sl_max_red, self.lbl_max_red_title = self._add_slider(side_panel, 6, 40, 26)

        self.var_live = tk.BooleanVar(value=False)
        self.chk_live = ttk.Checkbutton(side_panel, variable=self.var_live)
        self.chk_live.pack(anchor=tk.W, pady=8)

        self.lbl_stats = ttk.Label(side_panel, text="", foreground="red")
        self.lbl_stats.pack(anchor=tk.W, pady=3)

        self.lbl_help = ttk.Label(side_panel, font=("Segoe UI", 9, "italic"), wraplength=270)
        self.lbl_help.pack(anchor=tk.W, pady=10)

    def _add_slider(self, parent, val_from, val_to, default):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=3)
        lbl_title = ttk.Label(frame, text="")
        lbl_title.pack(anchor=tk.W)
        lbl_val = ttk.Label(frame, text=str(default))
        lbl_val.pack(anchor=tk.E)
        slider = ttk.Scale(frame, from_=val_from, to=val_to, value=default, command=lambda v: self._on_slider_change(lbl_val, v))
        slider.pack(fill=tk.X)
        slider.lbl_ref = lbl_val
        return slider, lbl_title
        
    def _set_slider_values_safely(self, p):
        """ Csúszkák frissítése úgy, hogy ne váltsanak ki nem kívánt eseményeket. """
        self._updating_ui = True
        try:
            self.sl_low.set(p.low_f)
            self.sl_high.set(p.high_f)
            self.sl_thresh.set(p.threshold_db)
            self.sl_max_dur.set(p.max_pop_duration_ms)
            self.sl_max_red.set(p.max_reduction_db)
        finally:
            self._updating_ui = False    

    def _update_language_text(self):
        t = LANG[self.cur_lang]
        self.title(t['title'])
        self.btn_open.config(text=t['open'])
        self.btn_orig.config(text=t['orig'])
        self.btn_filtered.config(text=t['filtered'])
        self.btn_delta.config(text=t['delta_on'] if self.delta_mode else t['delta_off'])
        self.btn_stop.config(text=t['stop'])
        self.btn_export_labels.config(text=t['export_labels'])
        self.btn_reset_zoom.config(text=t['reset_zoom'])
        self.btn_auto_tune.config(text=t['auto_tune'])
        self.btn_save_preset.config(text=t['save_preset'])
        self.btn_load_preset.config(text=t['load_preset'])
        self.btn_lang.config(text=t['lang_btn'])
        self.btn_about.config(text=t['about'])
        self.btn_save_wav.config(text=t['save_wav'])

        self.btn_global_mode.config(text=t['btn_global_mode'])
        self.btn_clear_reg.config(text=t['btn_clear_reg'])

        self.lbl_settings_head.config(text=t['settings_head'])
        self.presets_frame.config(text="Presets")
        self.mode_frame.config(text="Mód / Control" if self.cur_lang=='HU' else "Mode / Control")
        self.lbl_low_title.config(text=t['lbl_low'])
        self.lbl_high_title.config(text=t['lbl_high'])
        self.lbl_thresh_title.config(text=t['lbl_thresh'])
        self.lbl_max_dur_title.config(text=t['lbl_max_dur'])
        self.lbl_max_red_title.config(text=t['lbl_max_red'])
        self.chk_live.config(text=t['live_check'])
        self.lbl_help.config(text=t['help_text'])

        if self.audio is None:
            self.lbl_info.config(text=t['no_file'])
        self.wave_canvas.redraw()

    def _toggle_language(self):
        self.cur_lang = 'EN' if self.cur_lang == 'HU' else 'HU'
        self._update_language_text()

    def _regions_sidecar_path(self):
        if self.audio is None:
            return None
        base, _ = os.path.splitext(self.audio.path)
        return base + ".popregions.json"

    def _save_custom_regions(self):
        path = self._regions_sidecar_path()
        if path is None:
            return
        try:
            data = []
            for i, reg in enumerate(self.custom_regions):
                data.append(dict(
                    index=i,
                    start_sample=reg['start_sample'],
                    end_sample=reg['end_sample'],
                    start_t=reg['start_t'],
                    end_t=reg['end_t'],
                    params=reg['params'].to_dict(),
                ))
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_custom_regions(self):
        self.custom_regions = []
        path = self._regions_sidecar_path()
        if path is None or not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return

        tolerance_s = self.REGION_MATCH_TOLERANCE_S
        for entry in data:
            saved_start_t = entry.get('start_t', 0.0)
            match = None
            for s_t, e_t, _ in self.segments:
                if abs(s_t - saved_start_t) <= tolerance_s:
                    match = (s_t, e_t)
                    break
            if match is None:
                continue
            s_t, e_t = match
            try:
                params = core.PopParams.from_dict(entry.get('params', {}))
            except Exception:
                continue
            self.custom_regions.append({
                'start_sample': int(round(s_t * self.audio.fs)),
                'end_sample': int(round(e_t * self.audio.fs)),
                'start_t': s_t,
                'end_t': e_t,
                'params': params,
            })

    def _set_global_mode(self):
        self.selected_region_index = None
        self.sl_low.set(self.params.low_f)
        self.sl_high.set(self.params.high_f)
        self.sl_thresh.set(self.params.threshold_db)
        self.sl_max_dur.set(self.params.max_pop_duration_ms)
        self.sl_max_red.set(self.params.max_reduction_db)
        if self.audio:
            self.lbl_info.config(text=f"{self.audio.path} | 🌐 Globális mód")
        self.wave_canvas.redraw()

    def _clear_selected_region(self):
        if self.selected_region_index is not None and 0 <= self.selected_region_index < len(self.custom_regions):
            self.custom_regions.pop(self.selected_region_index)
            self.selected_region_index = None
            self.clean_samples = None
            self._clean_samples_from_sample = None
            self._save_custom_regions()
            self.lbl_info.config(text=f"🗑️ Egyedi beállítás törölve, visszatérve globálisba.")
            self._set_global_mode()
        else:
            messagebox.showinfo("Info", "Nincs kiválasztva egyedi régió." if self.cur_lang=='HU' else "No custom region selected.")

    def _on_slider_change(self, label, val):
        label.config(text=f"{float(val):.0f}")
        
        # Ha épp kódból frissítjük a csúszkákat, megállunk, hogy ne írjuk felül az értékeket
        if getattr(self, '_updating_ui', False):
            return

        if self.selected_region_index is not None and 0 <= self.selected_region_index < len(self.custom_regions):
            reg = self.custom_regions[self.selected_region_index]
            p = reg['params']
            p.low_f = float(self.sl_low.get())
            p.high_f = float(self.sl_high.get())
            p.threshold_db = float(self.sl_thresh.get())
            p.max_pop_duration_ms = float(self.sl_max_dur.get())
            p.max_reduction_db = float(self.sl_max_red.get())
            self.clean_samples = None
            self._clean_samples_from_sample = None
            if self._region_save_job is not None:
                self.after_cancel(self._region_save_job)
            self._region_save_job = self.after(400, self._save_custom_regions)
        elif self.var_live.get() and self.audio is not None:
            if self._live_debounce_job is not None:
                self.after_cancel(self._live_debounce_job)
            self._live_debounce_job = self.after(150, self._trigger_live_detection)

    def _process_queue(self):
        try:
            while True:
                msg_type, data = self.task_queue.get_nowait()
                if msg_type == "PROGRESS":
                    pct, msg = data
                    if hasattr(self, 'prog_dialog') and self.prog_dialog.winfo_exists():
                        self.prog_dialog.update_progress(pct, msg)
                        
                elif msg_type == "FILE_LOADED":
                    self.audio, self.cache = data
                    self.selected_region_index = None
                    self.lbl_info.config(text=f"{self.audio.path} | {self.audio.fs} Hz, {self.audio.duration_s:.2f} s")
                    self.play_start_time = 0.0
                    self._update_detection()
                    self._load_custom_regions()
                    if hasattr(self, 'prog_dialog') and self.prog_dialog.winfo_exists():
                        self.prog_dialog.destroy()
                    self.wave_canvas.load_audio(self.audio)
                    
                elif msg_type == "SAVE_READY":
                    current_params, analyses, segments, clean, path = data
                    self.params = current_params
                    self.analyses = analyses
                    self.segments = segments
                    self.clean_samples = clean
                    self._clean_samples_from_sample = 0
                    total_dur = sum(seg[1] - seg[0] for seg in self.segments)
                    t = LANG[self.cur_lang]
                    self.lbl_stats.config(text=t['detected_text'].format(count=len(self.segments), dur=total_dur))
                    if hasattr(self, 'prog_dialog') and self.prog_dialog.winfo_exists():
                        self.prog_dialog.destroy()
                    self.wave_canvas.redraw()
                    core.save_wav(self.audio, self.clean_samples, path)
                    messagebox.showinfo("OK", f"File saved:\n{path}")
                    
                elif msg_type == "PLAY_FILTERED_READY":
                    clean, start_sample = data
                    self.clean_samples = clean
                    self._clean_samples_from_sample = start_sample
                    self.btn_filtered.config(state='normal', text=LANG[self.cur_lang]['filtered'])
                    self._start_filtered_playback(start_sample)
                    
                elif msg_type == "LIVE_UPDATE_READY":
                    params, analyses, segments = data
                    self.params = params
                    self.analyses = analyses
                    self.segments = segments
                    self.clean_samples = None
                    self._clean_samples_from_sample = None
                    total_dur = sum(seg[1] - seg[0] for seg in self.segments)
                    t = LANG[self.cur_lang]
                    self.lbl_stats.config(text=t['detected_text'].format(count=len(self.segments), dur=total_dur))
                    self.wave_canvas.redraw()
                    
                elif msg_type == "ERROR":
                    if hasattr(self, 'prog_dialog') and self.prog_dialog.winfo_exists():
                        self.prog_dialog.destroy()
                    if hasattr(self, 'btn_filtered'):
                        self.btn_filtered.config(state='normal', text=LANG[self.cur_lang]['filtered'])
                    messagebox.showerror("Error", f"An error occurred:\n{data}")
                    
        except queue.Empty:
            pass
        self.after(100, self._process_queue)

    def _open_file(self):
        path = filedialog.askopenfilename(filetypes=[("WAV Audio", "*.wav")])
        if not path:
            return

        self.prog_dialog = ProgressDialog(self, title=LANG[self.cur_lang]['prog_title'])

        def work():
            try:
                def cb(pct, msg): self.task_queue.put(("PROGRESS", (pct, msg)))
                audio = core.AudioFile(path, progress_callback=cb)
                cache = core.build_cache(audio, progress_callback=cb)
                self.task_queue.put(("FILE_LOADED", (audio, cache)))
            except Exception as e:
                self.task_queue.put(("ERROR", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _update_detection(self):
        if self.audio is None or self.cache is None:
            return

        self.params = self._get_current_params()
        self.analyses, self.segments = core.detect_all_from_cache(self.cache, self.params)
        self.clean_samples = None
        self._clean_samples_from_sample = None

        total_dur = sum(seg[1] - seg[0] for seg in self.segments)
        t = LANG[self.cur_lang]
        self.lbl_stats.config(text=t['detected_text'].format(count=len(self.segments), dur=total_dur))
        self.wave_canvas.redraw()

    def _trigger_live_detection(self):
        self._live_debounce_job = None
        if self.audio is None or self.cache is None:
            return
            
        current_params = self._get_current_params()
        
        def work():
            try:
                analyses, segments = core.detect_all_from_cache(self.cache, current_params)
                self.task_queue.put(("LIVE_UPDATE_READY", (current_params, analyses, segments)))
            except Exception:
                pass
                
        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _format_time_axis(value: float, span: float) -> str:
        v = max(0.0, value)
        hours = int(v // 3600)
        minutes = int((v % 3600) // 60)
        seconds = v % 60
        if span < 2.0:
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
        elif span < 30.0:
            return f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"
        elif span < 300.0:
            return f"{hours:02d}:{minutes:02d}:{seconds:04.1f}"
        else:
            return f"{hours:02d}:{minutes:02d}:{seconds:02.0f}"

    def _on_waveform_click(self, click_t: float):
        if self.audio is None:
            return

        click_sample = int(click_t * self.audio.fs)
        self.play_start_time = click_t
        self.wave_canvas.update_playhead(click_t)

        clicked_idx = None
        for idx, (s_t, e_t, _) in enumerate(self.segments):
            s_sample = int(s_t * self.audio.fs)
            e_sample = int(e_t * self.audio.fs)
            if s_sample <= click_sample <= e_sample:
                clicked_idx = idx
                break

        if clicked_idx is not None:
            s_t, e_t, _ = self.segments[clicked_idx]
            s_sample = int(s_t * self.audio.fs)

            existing_reg = next(
                (r for r in self.custom_regions if abs(r['start_sample'] - s_sample) <= int(self.REGION_MATCH_TOLERANCE_S * self.audio.fs)),
                None)

            if existing_reg:
                self.selected_region_index = self.custom_regions.index(existing_reg)
                p = existing_reg['params']

                # BIZTONSÁGOS FRISSÍTÉS az új segédfüggvénnyel:
                self._set_slider_values_safely(p)

                self.lbl_info.config(text=f"🎯 Egyedi pop #{self.selected_region_index + 1} kijelölve ({s_t:.2f}s)")
            else:
                self._set_global_mode()
        else:
            self._set_global_mode()

        self.wave_canvas.redraw()

    def _on_waveform_double_click(self, click_t: float):
        """ Dupla kattintás: Egyedi beállítás aktiválása / dezaktiválása (ki-be kapcsolás). """
        if self.audio is None:
            return

        click_sample = int(click_t * self.audio.fs)

        clicked_idx = None
        for idx, (s_t, e_t, _) in enumerate(self.segments):
            s_sample = int(s_t * self.audio.fs)
            e_sample = int(e_t * self.audio.fs)
            if s_sample <= click_sample <= e_sample:
                clicked_idx = idx
                break

        if clicked_idx is not None:
            s_t, e_t, _ = self.segments[clicked_idx]
            s_sample = int(s_t * self.audio.fs)
            e_sample = int(e_t * self.audio.fs)

            existing_reg = next(
                (r for r in self.custom_regions if abs(r['start_sample'] - s_sample) <= int(self.REGION_MATCH_TOLERANCE_S * self.audio.fs)),
                None)

            if existing_reg:
                # DEZAKTIVÁLÁS: Eltávolítjuk az egyedi régiót (visszaáll pirosra/globálisra)
                self.custom_regions.remove(existing_reg)
                self.selected_region_index = None
                self.clean_samples = None
                self._clean_samples_from_sample = None
                self._save_custom_regions()
                self._set_global_mode()
                self.lbl_info.config(text=f"🌐 Egyedi beállítás dezaktiválva ezen a popon.")
            else:
                # AKTIVÁLÁS: Létrehozzuk az egyedi régiót a jelenlegi globális értékekkel (átsárgul)
                new_p = copy.deepcopy(self.params)
                self.custom_regions.append({
                    'start_sample': s_sample,
                    'end_sample': e_sample,
                    'start_t': s_t,
                    'end_t': e_t,
                    'params': new_p
                })
                self.selected_region_index = len(self.custom_regions) - 1
                self.clean_samples = None
                self._clean_samples_from_sample = None

                self.sl_low.set(new_p.low_f)
                self.sl_high.set(new_p.high_f)
                self.sl_thresh.set(new_p.threshold_db)
                self.sl_max_dur.set(new_p.max_pop_duration_ms)
                self.sl_max_red.set(new_p.max_reduction_db)

                self._save_custom_regions()
                self.lbl_info.config(text=f"🎯 Egyedi pop #{self.selected_region_index + 1} aktiválva ({s_t:.2f}s)")

        self.wave_canvas.redraw()

    def _reset_zoom(self):
        self.wave_canvas.reset_zoom()

    def _toggle_delta(self):
        self.delta_mode = not self.delta_mode
        t = LANG[self.cur_lang]
        if self.delta_mode:
            self.btn_delta.config(bg="#ff4d4d", fg="white", text=t['delta_on'])
        else:
            self.btn_delta.config(bg="#e1e1e1", fg="black", text=t['delta_off'])

    def _auto_tune(self):
        self.sl_low.set(37)
        self.sl_high.set(172)
        self.sl_thresh.set(13)
        self.sl_max_dur.set(180)
        self.sl_max_red.set(26)
        self._update_detection()

    def _save_preset(self):
        preset_data = {
            'low_f': float(self.sl_low.get()),
            'high_f': float(self.sl_high.get()),
            'threshold_db': float(self.sl_thresh.get()),
            'max_pop_duration_ms': float(self.sl_max_dur.get()),
            'max_reduction_db': float(self.sl_max_red.get()),
        }
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Preset", "*.json")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=4)
            messagebox.showinfo("OK", "Preset saved!" if self.cur_lang == 'EN' else "Profil mentve!")

    def _load_preset(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Preset", "*.json")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.sl_low.set(data.get('low_f', 37))
                self.sl_high.set(data.get('high_f', 172))
                self.sl_thresh.set(data.get('threshold_db', 13))
                self.sl_max_dur.set(data.get('max_pop_duration_ms', 180))
                self.sl_max_red.set(data.get('max_reduction_db', 26))
                self._update_detection()
                messagebox.showinfo("OK", "Preset loaded!" if self.cur_lang == 'EN' else "Profil betöltve!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load preset:\n{e}")

    def _show_about(self):
        """ Angol nyelvű Névjegy ablak belső görgetősávval az összes licenc megjelenítéséhez """
        about_win = tk.Toplevel(self)
        about_win.title("About")
        about_win.geometry("450x520")
        about_win.resizable(False, False)
        about_win.transient(self)
        about_win.grab_set()

        # Görgethető felület létrehozása Canvas és Scrollbar segítségével
        canvas = tk.Canvas(about_win, borderwidth=0, highlightthickness=0, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(about_win, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#f0f0f0", padx=20, pady=15)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Egérgörgő támogatás a görgetéshez
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        about_win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # --- FEJLÉC ---
        tk.Label(
            scroll_frame,
            text="Pop Filter Pro",
            font=("Segoe UI", 16, "bold"),
            fg="#005fb8",
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(0, 2))

        tk.Label(
            scroll_frame,
            text="Version: 2.00",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(0, 15))

        # --- KÖSZÖNETNYILVÁNÍTÁS / ACKNOWLEDGMENTS ---
        tk.Label(
            scroll_frame,
            text="Acknowledgments:",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(0, 4))

        ack_text = (
            "Special thanks to the open-source community and researchers "
            "without whose work this software could not have been created:\n"
            "• SciPy, NumPy & SoundDevice development teams\n"
            "• HPSS (Harmonic-Percussive Source Separation) & Wiener filtering researchers"
        )
        tk.Label(
            scroll_frame,
            text=ack_text,
            justify="left",
            wraplength=380,
            font=("Segoe UI", 9),
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(0, 15))

        # --- LICENCEK / OPEN SOURCE LICENSES ---
        tk.Label(
            scroll_frame,
            text="Licenses / Open Source Licenses:",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(0, 4))

        lic_summary = (
            "• Pop Filter Pro (this program): GNU General Public License v3.0 (GPLv3)\n"
            "• Python Core: Python Software Foundation License (PSFL)\n"
            "• NumPy & SciPy: BSD 3-Clause License\n"
            "• SoundDevice / PortAudio: MIT License\n"
            "• Tcl/Tk: TCL/TK License (BSD-style)\n"
            "• PyInstaller bootloader: GPLv2 + linking exception"
        )
        tk.Label(
            scroll_frame,
            text=lic_summary,
            justify="left",
            wraplength=380,
            font=("Segoe UI", 9),
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(0, 15))

        # --- RÉSZLETES LICENC SZÖVEGEK (A CSÚSZKÁVAL GÖRGETHETŐ RÉSZ) ---
        tk.Label(
            scroll_frame,
            text="Full License Details:",
            font=("Segoe UI", 9, "bold"),
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(0, 4))

        full_licenses = (
            "--- Pop Filter Pro - GNU General Public License v3.0 (GPLv3) ---\n"
            "Copyright (C) 2026 szabiz. This program is free software: you can "
            "redistribute it and/or modify it under the terms of the GNU General "
            "Public License as published by the Free Software Foundation, either "
            "version 3 of the License, or (at your option) any later version. "
            "This program is distributed WITHOUT ANY WARRANTY. If you distribute "
            "modified versions, the source code must remain available under the "
            "same license. Full text: https://www.gnu.org/licenses/gpl-3.0.html\n\n"
            "--- Python Software Foundation License (PSFL) ---\n"
            "Python is distributed under the PSFL license, allowing full use, modification, "
            "and distribution of code and binaries.\n\n"
            "--- BSD 3-Clause License (NumPy, SciPy) ---\n"
            "Redistribution and use in source and binary forms, with or without modification, "
            "are permitted provided that the following conditions are met:\n"
            "1. Redistributions of source code must retain the above copyright notice.\n"
            "2. Redistributions in binary form must reproduce the above copyright notice.\n"
            "3. Neither the name of the copyright holder nor the names of its contributors "
            "may be used to endorse or promote products derived from this software.\n\n"
            "--- MIT License (SoundDevice, PortAudio) ---\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files, to deal in the Software "
            "without restriction, including without limitation the rights to use, copy, "
            "modify, merge, publish, distribute, sublicense, and/or sell copies.\n\n"
            "--- TCL/TK License (Tcl/Tk, BSD-style) ---\n"
            "Permission to use, copy, modify, and distribute this software and its "
            "documentation for any purpose and without fee is hereby granted, provided "
            "that the copyright notice appears in all copies. Provided \"as is\" without "
            "warranty.\n\n"
            "--- PyInstaller Bootloader License (GPLv2 + exception) ---\n"
            "The compiled bootloader that runs this .exe is covered by the GPL license "
            "WITH A SPECIAL EXCEPTION which allows distributing the resulting program "
            "under any license (including this program's own GPLv3), without forcing "
            "extra obligations beyond what is already stated above."
        )

        tk.Label(
            scroll_frame,
            text=full_licenses,
            justify="left",
            wraplength=380,
            font=("Segoe UI", 8),
            fg="#444444",
            bg="#e8e8e8",
            relief="solid",
            bd=1,
            padx=8,
            pady=8
        ).pack(anchor="w", pady=(0, 15))

        # --- ELVÁLASZTÓ VONAL ---
        ttk.Separator(scroll_frame, orient="horizontal").pack(fill="x", pady=10)

        # --- LÁBLÉC ---
        tk.Label(
            scroll_frame,
            text="Soli Deo Gloria",
            font=("Georgia", 12, "italic", "bold"),
            fg="#222222",
            bg="#f0f0f0"
        ).pack(anchor="center", pady=(5, 2))

        tk.Label(
            scroll_frame,
            text="Copyright © szabiz 2026",
            font=("Segoe UI", 9),
            fg="#555555",
            bg="#f0f0f0"
        ).pack(anchor="center")

        tk.Label(
            scroll_frame,
            text="Free & Open Source Software - Licensed under GPLv3",
            font=("Segoe UI", 8, "italic"),
            fg="#777777",
            bg="#f0f0f0"
        ).pack(anchor="center", pady=(2, 0))

    def _start_playback_clock(self, start_time):
        self.play_start_time = max(0.0, float(start_time))
        self.play_start_position = self.play_start_time
        self.playback_started_monotonic = time.monotonic()
        self.playback_duration = max(0.0, self.audio.duration_s - self.play_start_position)
        self.playback_active = True
        if self.playback_job is not None:
            try:
                self.after_cancel(self.playback_job)
            except Exception:
                pass
        self.playback_job = self.after(30, self._update_playhead)

    def _update_playhead(self):
        """ Villámgyors natív Canvas lejátszófej frissítés """
        if not self.playback_active or self.audio is None:
            self.playback_job = None
            return

        elapsed = time.monotonic() - self.playback_started_monotonic
        pos = self.play_start_position + elapsed

        if pos >= self.audio.duration_s:
            self.play_start_time = self.audio.duration_s
            self.playback_active = False
            self.playback_job = None
            self.wave_canvas.update_playhead(self.play_start_time)
            return

        self.play_start_time = pos
        self.wave_canvas.update_playhead(pos)
        self.playback_job = self.after(30, self._update_playhead)

    def _play_orig(self):
        if self.audio is None:
            return
        sd.stop()
        start_sample = int(self.play_start_time * self.audio.fs)
        sd.play(self.audio.samples[start_sample:], self.audio.fs)
        self._start_playback_clock(self.play_start_time)

    def _play_filtered(self):
        if self.audio is None:
            return
        sd.stop()

        start_sample = int(self.play_start_time * self.audio.fs)
        preview_duration_samples = int(30.0 * self.audio.fs)

        has_cached = (
            self.clean_samples is not None
            and getattr(self, '_clean_samples_from_sample', None) is not None
            and self._clean_samples_from_sample <= start_sample
            and start_sample < self._clean_samples_from_sample + preview_duration_samples
        )

        if has_cached:
            self._start_filtered_playback(start_sample)
            return

        self.btn_filtered.config(state='disabled', text=LANG[self.cur_lang]['rendering'])

        params = self.params
        cache = self.cache
        audio = self.audio
        custom_regs = self.custom_regions

        def work():
            try:
                clean = core.render_all_from_cache(audio, cache, params, start_sample=start_sample, max_duration_s=30.0, custom_regions=custom_regs)
                self.task_queue.put(("PLAY_FILTERED_READY", (clean, start_sample)))
            except Exception as e:
                self.task_queue.put(("ERROR", str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _start_filtered_playback(self, start_sample: int):
        if self.delta_mode:
            delta_samples = self.audio.samples[start_sample:] - self.clean_samples[start_sample:]
            sd.play(delta_samples, self.audio.fs)
        else:
            sd.play(self.clean_samples[start_sample:], self.audio.fs)
            
        self._start_playback_clock(self.play_start_time)

    def _stop_audio(self):
        sd.stop()
        self.playback_active = False
        if self.playback_job is not None:
            try:
                self.after_cancel(self.playback_job)
            except Exception:
                pass
            self.playback_job = None
        self.wave_canvas.redraw()

    def _export_audacity_labels(self):
        if self.audio is None:
            return
        if not self.segments:
            messagebox.showinfo(
                "Audacity",
                "Nincs jelenleg kijelölt pop-szakasz." if self.cur_lang == 'HU' else "There are no detected pop segments to export.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Audacity Labels", "*.txt"), ("Text file", "*.txt")]
        )
        if not path:
            return

        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            for i, (start_t, end_t, peak) in enumerate(self.segments, 1):
                f.write(f"{start_t:.6f}\t{end_t:.6f}\tPop {i:03d} ({peak:.1f} dB)\n")

        messagebox.showinfo(
            "Audacity",
            (f"Elmentve: {path}\n\nAudacityben: Fájl → Importálás → Címkék (Labels)."
             if self.cur_lang == 'HU' else
             f"Saved: {path}\n\nIn Audacity: File → Import → Labels."))

    def _get_current_params(self):
        p = core.PopParams()
        p.low_f = float(self.sl_low.get())
        p.high_f = float(self.sl_high.get())
        p.threshold_db = float(self.sl_thresh.get())
        p.max_pop_duration_ms = float(self.sl_max_dur.get())
        p.max_reduction_db = float(self.sl_max_red.get())
        return p

    def _save_file(self):
        if self.audio is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Audio", "*.wav")])
        if not path:
            return

        current_params = self._get_current_params()
        custom_regs = self.custom_regions
        self.prog_dialog = ProgressDialog(self, title=LANG[self.cur_lang]['prog_title'])

        def work():
            try:
                def cb(pct, msg): self.task_queue.put(("PROGRESS", (pct, msg)))
                analyses, segments = core.detect_all_from_cache(self.cache, current_params)
                clean = core.render_all_from_cache(self.audio, self.cache, current_params, progress_callback=cb, custom_regions=custom_regs)
                self.task_queue.put(("SAVE_READY", (current_params, analyses, segments, clean, path)))
            except Exception as e:
                self.task_queue.put(("ERROR", str(e)))

        threading.Thread(target=work, daemon=True).start()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = PopFilterApp()
    app.mainloop()
