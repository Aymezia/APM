import os
import time
import threading
from collections import deque
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
import urllib.request
import json
import ctypes
import sys
import http.server
import socketserver
import socket

from apm_config import load_config as load_app_config, save_config as save_app_config
from apm_overlay import build_overlay_html
from apm_stats import export_history as export_history_helper, take_snapshot as take_snapshot_helper, build_session_summary
from apm_ui import build_main_window
from apm_events import start_listeners as start_listeners_helper, stop_listeners as stop_listeners_helper
from apm_streaming import start_api_server as start_api_server_helper, stop_api_server as stop_api_server_helper, open_overlay_in_browser as open_overlay_in_browser_helper

try:
    from pynput import keyboard, mouse
except ImportError:
    keyboard = None
    mouse = None

SESSION_SECONDS = 5 * 60 * 60
SMOOTH_WINDOW = 60.0

class APMMonitor:
    def __init__(self):
        self.events = deque()
        self.session_start = time.time()
        self.high_apm = 0
        self.low_apm = None
        self.total_actions = 0
        self.overlay = True
        # configurable parameters
        self.bg = "#0f1720"
        self.fg = "#e6eef6"
        self.accent = "#00c2ff"
        self.font_size = 36
        self.width = 520
        self.height = 320
        self.opacity = 0.92
        # use short smoothing by default so APM drops quickly when idle
        self.smooth_window = 5.0
        self.session_seconds = SESSION_SECONDS
        self.show_decimals = False
        self.compact_mode = False
        self.mini_mode = False
        self.obs_mode = False
        self.streamer_mode = False
        self.api_enabled = False
        self.api_port = 8765
        self.api_running = False
        self._api_thread = None
        self._api_server = None
        # OBS WebSocket integration
        self.obs_ws_enabled = False
        self.obs_ws_host = 'localhost'
        self.obs_ws_port = 4455
        self.obs_ws_password = ''
        self._obs_thread = None
        self._obs_client = None
        self._obs_running = False
        self.scene_on_stream_start = ''
        self.scene_on_stream_stop = ''
        self.theme = 'dark'
        self.start_minimized = False
        self.alert_enabled = True
        self.alert_high_threshold = 180
        self.alert_low_threshold = 20
        self.alert_state = None
        self.high_start_time = None
        self.low_start_time = None
        self.cps = 0
        self.current_profile = 'Default'
        self.focus_mode = False
        self.paused = False
        self.pause_started_at = None
        self.session_count = 0
        self.total_active_seconds = 0
        self.last_snapshot_path = None
        # game profiles presets
        self.profiles = {
            'Default': {'smooth_window': 5.0, 'opacity': 0.92, 'font_size': 36, 'alert_high_threshold': 180, 'alert_low_threshold': 20, 'compact_mode': False, 'focus_mode': False, 'mini_mode': False},
            'FPS': {'smooth_window': 3.0, 'opacity': 0.85, 'font_size': 40, 'alert_high_threshold': 220, 'alert_low_threshold': 35, 'compact_mode': True, 'focus_mode': False, 'mini_mode': False},
            'RTS': {'smooth_window': 8.0, 'opacity': 0.92, 'font_size': 34, 'alert_high_threshold': 170, 'alert_low_threshold': 18, 'compact_mode': False, 'focus_mode': False, 'mini_mode': False},
            'MOBA': {'smooth_window': 6.0, 'opacity': 0.9, 'font_size': 36, 'alert_high_threshold': 200, 'alert_low_threshold': 25, 'compact_mode': True, 'focus_mode': False, 'mini_mode': False},
            'Coaching': {'smooth_window': 4.0, 'opacity': 0.95, 'font_size': 44, 'alert_high_threshold': 210, 'alert_low_threshold': 30, 'compact_mode': False, 'focus_mode': True, 'mini_mode': False},
            'Streaming': {'smooth_window': 3.0, 'opacity': 0.96, 'font_size': 42, 'alert_high_threshold': 240, 'alert_low_threshold': 35, 'compact_mode': True, 'focus_mode': False, 'mini_mode': False},
        }

        self.history = []
        self.history_interval = 15
        self._last_history_record = 0
        self.remote_urls = []
        self.gaming_zone = None

        # remote stats
        self.remote_enabled = False
        self.remote_url = ""
        self.remote_interval = 30
        self._last_remote_fetch = 0

        self.config_path = os.path.join(os.path.dirname(__file__), "apm_config.json")
        self.apm_history = deque(maxlen=60)
        self.load_config()

        self.root = tk.Tk()
        self.root.title("APM Overlay")
        self.root.geometry(f"{self.width}x{self.height}+100+100")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", self.overlay)
        try:
            self.root.attributes("-alpha", self.opacity)
        except Exception:
            pass
        self.root.configure(background=self.bg)
        # if API enabled start server
        if self.api_enabled:
            try:
                self.start_api_server()
            except Exception:
                pass
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind("<Escape>", lambda e: self.quit())
        # shortcuts
        self.root.bind("<Control-Shift-O>", lambda e: (self.overlay_var.set(not self.overlay_var.get()), self.toggle_overlay()))
        self.root.bind("<Control-Shift-S>", lambda e: self.open_settings())
        self.root.bind("<F1>", lambda e: (self.overlay_var.set(not self.overlay_var.get()), self.toggle_overlay()))
        self.root.bind("<Control-Shift-R>", lambda e: self.reset_stats())
        self.root.bind("<F9>", lambda e: self.reset_stats())

        self.create_widgets()
        self.apply_theme()
        self.update_ui_mode()
        self.apply_profile(self.current_profile)
        if self.start_minimized:
            try:
                self.root.iconify()
            except Exception:
                pass
        # apply overlay mode settings (click-through + disable dragging) if overlay default is True
        if self.overlay:
            try:
                self.toggle_overlay()
            except Exception:
                pass
        self.start_listeners()
        self.update_loop()

    def create_widgets(self):
        self.widgets = build_main_window(self)
        self.frame = self.widgets['frame']
        self.current_label = self.widgets['current_label']
        self.stats_label = self.widgets['stats_label']
        self.summary_label = self.widgets['summary_label']
        self.extra_label = self.widgets['extra_label']
        self.session_summary_label = self.widgets['session_summary_label']
        self.remote_label = self.widgets['remote_label']
        self.segment_label = self.widgets['segment_label']
        self.graph_canvas = self.widgets['graph_canvas']
        self.timer_label = self.widgets['timer_label']
        self.controls = self.widgets['controls']
        self.overlay_var = self.widgets['overlay_var']
        self.overlay_btn = self.widgets['overlay_btn']
        self.settings_btn = self.widgets['settings_btn']
        self.reset_btn = self.widgets['reset_btn']
        self.font_scale = self.widgets['font_scale']
        self.help_label = self.widgets['help_label']
        self.mini_toggle_btn = self.widgets['mini_toggle_btn']
        self.pause_btn = self.widgets['pause_btn']
        self.focus_btn = self.widgets['focus_btn']
        self.copy_btn = self.widgets['copy_btn']
        self.snapshot_btn = self.widgets['snapshot_btn']

        self.make_draggable(self.frame)
        self.make_draggable(self.current_label)

        self.root.bind("<F10>", lambda e: (self.overlay_var.set(not self.overlay_var.get()), self.toggle_overlay()))
        self.root.bind("<F11>", lambda e: self.toggle_focus_mode())
        self.root.bind("<Control-Shift-P>", lambda e: self.toggle_pause())
        self.root.bind("<Control-Shift-C>", lambda e: self.copy_stats())
        self.root.bind("<Control-Shift-Y>", lambda e: self.take_snapshot())

    def start_listeners(self):
        start_listeners_helper(self)

    def stop_listeners(self):
        stop_listeners_helper(self)

    def action_event(self, *args):
        # If called from keyboard listener, args[0] may be a Key object
        now = time.time()
        try:
            evt = args[0]
        except Exception:
            evt = None

        # handle F1: when overlay is active and mouse is over overlay, toggle overlay off
        try:
            if evt is not None and keyboard and getattr(keyboard, 'Key', None) and evt == keyboard.Key.f1:
                if self.overlay and self.is_mouse_over_overlay():
                    # switch overlay off to allow interaction
                    self.overlay_var.set(False)
                    self.toggle_overlay()
                    return
        except Exception:
            pass

        # record generic action (mouse/keys) for APM
        self.events.append(now)
        self.total_actions += 1
        self.trim_events(now)

    def compute_dpm(self):
        now = time.time()
        cutoff = now - 60.0
        count = sum(1 for event_time in self.events if event_time >= cutoff)
        return count

    def play_alert(self, tone: str):
        try:
            if sys.platform.startswith('win'):
                import winsound
                freq = 750 if tone == 'high' else 400
                winsound.Beep(freq, 120)
        except Exception:
            pass

    def trim_events(self, now):
        cutoff = now - self.session_seconds
        while self.events and self.events[0] < cutoff:
            self.events.popleft()

    def compute_apm(self):
        now = time.time()
        window_cutoff = now - self.smooth_window
        count = 0
        for event_time in reversed(self.events):
            if event_time >= window_cutoff:
                count += 1
            else:
                break
        return count * (60.0 / self.smooth_window)

    def compute_average(self):
        elapsed = time.time() - self.session_start
        if elapsed < 1:
            return 0.0
        interval = min(elapsed, self.session_seconds)
        return self.total_actions * 60.0 / interval

    def update_loop(self):
        now = time.time()
        if self.paused:
            try:
                self.timer_label.config(text=f"Temps: {self._format_duration(int(time.time() - self.session_start))} (Pause)")
            except Exception:
                pass
            self.root.after(250, self.update_loop)
            return
        self.trim_events(now)
        apm_float = self.compute_apm()
        # update high/low using floats to avoid rounding bias
        # ignore zero/near-zero APM (idle) when updating the recorded minimum
        self.high_apm = max(self.high_apm, apm_float)
        if apm_float > 0.5:  # consider this an active APM sample
            if self.low_apm is None or apm_float < self.low_apm:
                self.low_apm = apm_float

        avg = self.compute_average()
        duration = int(now - self.session_start)
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)

        # format display values
        if self.show_decimals:
            apm_display = f"{apm_float:.1f}"
            max_display = f"{self.high_apm:.1f}"
            min_display = f"{self.low_apm:.1f}" if self.low_apm is not None else "-"
        else:
            apm_display = f"{int(round(apm_float))}"
            max_display = f"{int(round(self.high_apm))}"
            min_display = f"{int(round(self.low_apm))}" if self.low_apm is not None else "-"

        self.current_label.config(text=f"APM: {apm_display}")
        self.cps = self.compute_cps()
        dpm = self.compute_dpm()
        self.stats_label.config(text=f"Avg: {avg:.1f} | Best: {max_display} | Worst: {min_display}")
        self.summary_label.config(text=f"CPS: {self.cps} | DPM: {dpm} | Sessions: {self.session_count} | Active: {self._format_duration(duration)}")
        self.extra_label.config(text=f"Actions: {self.total_actions} | Trend: {'up' if apm_float > avg else 'down'}")
        if hasattr(self, 'session_summary_label'):
            self.session_summary_label.config(text=build_session_summary(apm_float, avg, self.cps, dpm, self.total_actions, self.session_count, duration, self.high_apm, self.low_apm))
        self.record_history(now, apm_float, self.cps, dpm)
        self.update_segment_labels(apm_float, avg)
        self.update_gaming_zone(apm_float)
        self.draw_graph(apm_float)
        if self.alert_enabled:
            if apm_float >= self.alert_high_threshold and self.alert_state != 'high':
                self.alert_state = 'high'
                self.high_start_time = self.high_start_time or now
                self.root.configure(background="#881fff")
                if now - self.high_start_time > 1:
                    self.play_alert('high')
            elif apm_float <= self.alert_low_threshold and self.alert_state != 'low':
                self.alert_state = 'low'
                self.low_start_time = self.low_start_time or now
                self.current_label.config(text=f"APM: {apm_display} (LOW)")
                if now - self.low_start_time > 1:
                    self.play_alert('low')
            elif self.alert_low_threshold < apm_float < self.alert_high_threshold:
                self.alert_state = None
                self.high_start_time = None
                self.low_start_time = None
                self.apply_theme()
        self.timer_label.config(text=f"Temps: {hours:02}:{minutes:02}:{seconds:02}")
        self.root.after(250, self.update_loop)
        # remote stats periodic fetch
        try:
            if self.remote_enabled and self.remote_url and (now - self._last_remote_fetch) > self.remote_interval:
                self._last_remote_fetch = now
                self.fetch_remote_stats(show_popup=False)
        except Exception:
            pass

        pass

    def toggle_overlay(self):
        self.overlay = self.overlay_var.get()
        self.root.attributes("-topmost", self.overlay)
        self.root.overrideredirect(self.overlay)
        try:
            self.root.attributes("-alpha", self.opacity if self.overlay else 1.0)
        except Exception:
            pass
        # enable click-through when overlay is active, and disable dragging
        if self.overlay:
            self.set_clickthrough(True)
            self.disable_dragging()
            try:
                self.controls.pack_forget()
                self.help_label.pack_forget()
            except Exception:
                pass
            if self.compact_mode:
                self.root.geometry(f"{self.width}x{int(self.height * 0.55)}+100+100")
        else:
            self.set_clickthrough(False)
            self.enable_dragging()
            try:
                self.controls.pack(fill="x")
                self.help_label.pack(fill="x", pady=(8, 0))
            except Exception:
                pass
            self.root.geometry(f"{self.width}x{self.height}+100+100")
            self.root.resizable(False, False)
        return

    def apply_profile(self, name: str):
        profile = self.profiles.get(name)
        if not profile:
            return
        self.current_profile = name
        try:
            self.smooth_window = float(profile.get('smooth_window', self.smooth_window))
            self.opacity = float(profile.get('opacity', self.opacity))
            self.font_size = int(profile.get('font_size', self.font_size))
            self.alert_high_threshold = int(profile.get('alert_high_threshold', self.alert_high_threshold))
            self.alert_low_threshold = int(profile.get('alert_low_threshold', self.alert_low_threshold))
            self.compact_mode = bool(profile.get('compact_mode', self.compact_mode))
            self.focus_mode = bool(profile.get('focus_mode', self.focus_mode))
            self.font_scale.set(self.font_size)
            self.current_label.configure(font=("Consolas", self.font_size, "bold"))
            try:
                self.root.attributes("-alpha", self.opacity)
            except Exception:
                pass
        except Exception:
            pass
        self.update_ui_mode()
        self.save_config()

    def update_ui_mode(self):
        if self.mini_mode:
            self.graph_canvas.pack_forget()
            self.remote_label.pack_forget()
            self.segment_label.pack_forget()
            self.controls.pack_forget()
            self.help_label.pack_forget()
            self.current_label.configure(font=("Consolas", 28, "bold"))
            self.mini_toggle_btn.place(relx=1.0, x=-18, y=4, anchor='ne')
            self.root.geometry(f"{int(self.width * 0.55)}x{120}+100+100")
        else:
            if self.focus_mode:
                self.graph_canvas.pack_forget()
                self.remote_label.pack_forget()
                self.segment_label.pack_forget()
                self.current_label.configure(font=("Consolas", max(self.font_size + 12, 48), "bold"))
                self.summary_label.configure(font=("Consolas", 11, "bold"))
            else:
                if not self.graph_canvas.winfo_ismapped():
                    self.graph_canvas.pack(fill="x", pady=(4, 4))
                if not self.remote_label.winfo_ismapped():
                    self.remote_label.pack(fill="x", pady=(2, 0))
                if not self.segment_label.winfo_ismapped():
                    self.segment_label.pack(fill="x", pady=(2, 0))
                self.current_label.configure(font=("Consolas", self.font_size, "bold"))
                self.summary_label.configure(font=("Consolas", 9))
            if not self.controls.winfo_ismapped():
                self.controls.pack(fill="x")
            if not self.help_label.winfo_ismapped():
                self.help_label.pack(fill="x", pady=(8, 0))
            self.mini_toggle_btn.place_forget()
            self.root.geometry(f"{self.width}x{self.height}+100+100")

    def toggle_mini_mode(self):
        self.mini_mode = not self.mini_mode
        self.update_ui_mode()
        self.save_config()

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_started_at = time.time()
        else:
            if self.pause_started_at is not None:
                self.session_start += time.time() - self.pause_started_at
                self.pause_started_at = None
        self.save_config()
        self.update_ui_mode()

    def toggle_focus_mode(self):
        self.focus_mode = not self.focus_mode
        self.update_ui_mode()
        self.save_config()

    def copy_stats(self):
        text = f"APM: {int(round(self.compute_apm()))} | Avg: {self.compute_average():.1f} | CPS: {self.compute_cps()} | DPM: {self.compute_dpm()}"
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            pass

    def take_snapshot(self):
        try:
            path = take_snapshot_helper(self)
            if path:
                self.last_snapshot_path = path
                self.summary_label.config(text=f"Snapshot saved: {os.path.basename(path)}")
        except Exception:
            pass

    def _format_duration(self, seconds: int) -> str:
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def fetch_remote_stats(self, show_popup: bool = True):
        if not self.remote_urls and not self.remote_url:
            url = simpledialog.askstring("Remote URL", "Entrer l'URL des stats (JSON)")
            if not url:
                return
            self.remote_urls = [url.strip()]
            self.remote_url = self.remote_urls[0]
            self.remote_enabled = True
        elif self.remote_urls:
            self.remote_url = self.remote_urls[0]
        try:
            with urllib.request.urlopen(self.remote_url, timeout=6) as resp:
                text = resp.read().decode(errors='ignore')
                data = json.loads(text)
        except Exception as exc:
            if show_popup:
                messagebox.showerror("Erreur remote", f"Impossible de récupérer les stats :\n{exc}")
            return

        if isinstance(data, dict):
            apm = data.get('apm')
            maxv = data.get('max')
            minv = data.get('min')
            avg = data.get('avg')
            pieces = [f"APM:{apm}" if apm is not None else None,
                      f"Max:{maxv}" if maxv is not None else None,
                      f"Min:{minv}" if minv is not None else None,
                      f"Avg:{avg}" if avg is not None else None]
            summary = " ".join([p for p in pieces if p])
        else:
            summary = str(data)
        self.remote_label.config(text=f"Remote: {summary}")
        if show_popup:
            messagebox.showinfo("Remote stats", summary)

    # --- simple local HTTP API for stream overlays ---
    class _StatsHandler(http.server.BaseHTTPRequestHandler):
        def __init__(self, monitor, *args, **kwargs):
            self.monitor = monitor
            super().__init__(*args, **kwargs)

        def do_GET(self):
            if self.path.startswith('/stats'):
                try:
                    now = time.time()
                    apm = self.monitor.compute_apm()
                    cps = self.monitor.compute_cps()
                    dpm = self.monitor.compute_dpm()
                    payload = {
                        'apm': apm,
                        'cps': cps,
                        'dpm': dpm,
                        'high': self.monitor.high_apm,
                        'low': self.monitor.low_apm,
                        'time': now,
                    }
                    body = json.dumps(payload).encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception:
                    self.send_response(500)
                    self.end_headers()
            elif self.path.startswith('/overlay') or self.path.startswith('/overlay.html'):
                try:
                    body = build_overlay_html().encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception:
                    self.send_response(500)
                    self.end_headers()
            elif self.path.startswith('/stream'):
                # Server-Sent Events (SSE) endpoint for real-time push
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Connection', 'keep-alive')
                    self.end_headers()
                    # flush headers
                    try:
                        self.wfile.flush()
                    except Exception:
                        pass
                    # send events until client disconnects
                    while True:
                        now = time.time()
                        payload = {
                            'apm': self.monitor.compute_apm(),
                            'cps': self.monitor.compute_cps(),
                            'dpm': self.monitor.compute_dpm(),
                            'high': self.monitor.high_apm,
                            'low': self.monitor.low_apm,
                            'time': now,
                        }
                        data = json.dumps(payload)
                        try:
                            self.wfile.write(f"data: {data}\n\n".encode('utf-8'))
                            try:
                                self.wfile.flush()
                            except Exception:
                                pass
                        except Exception:
                            break
                        time.sleep(0.25)
                except Exception:
                    try:
                        self.send_response(500)
                        self.end_headers()
                    except Exception:
                        pass
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            # silence default logging
            return

    def start_api_server(self):
        start_api_server_helper(self)

    def stop_api_server(self):
        stop_api_server_helper(self)

    def open_overlay_in_browser(self):
        open_overlay_in_browser_helper(self)

    def get_stats_payload(self):
        return {
            'apm': self.compute_apm(),
            'cps': self.compute_cps(),
            'dpm': self.compute_dpm(),
            'high': self.high_apm,
            'low': self.low_apm,
            'time': time.time(),
        }

    def get_overlay_html(self):
        return build_overlay_html()

    def fetch_remote_stats(self, show_popup: bool = True):
        if not self.remote_url:
            url = simpledialog.askstring("Remote URL", "Entrer l'URL des stats (JSON)")
            if not url:
                return
            self.remote_url = url.strip()
            self.remote_enabled = True
        try:
            with urllib.request.urlopen(self.remote_url, timeout=6) as resp:
                text = resp.read().decode(errors='ignore')
                data = json.loads(text)
        except Exception as exc:
            if show_popup:
                messagebox.showerror("Erreur remote", f"Impossible de récupérer les stats :\n{exc}")
            return

        if isinstance(data, dict):
            apm = data.get('apm')
            maxv = data.get('max')
            minv = data.get('min')
            avg = data.get('avg')
            pieces = [f"APM:{apm}" if apm is not None else None,
                      f"Max:{maxv}" if maxv is not None else None,
                      f"Min:{minv}" if minv is not None else None,
                      f"Avg:{avg}" if avg is not None else None]
            summary = " ".join([p for p in pieces if p])
        else:
            summary = str(data)
        self.remote_label.config(text=f"Remote: {summary}")
        if show_popup:
            messagebox.showinfo("Remote stats", summary)

    def make_draggable(self, widget):
        # Allow dragging the main window by holding the widget
        def start_move(event):
            widget._drag_start_x = event.x
            widget._drag_start_y = event.y

        def do_move(event):
            x = self.root.winfo_x() + event.x - widget._drag_start_x
            y = self.root.winfo_y() + event.y - widget._drag_start_y
            self.root.geometry(f"+{x}+{y}")

        # store handlers so we can unbind when overlay is active
        widget._start_move_handler = start_move
        widget._do_move_handler = do_move
        widget.bind("<ButtonPress-1>", start_move)
        widget.bind("<B1-Motion>", do_move)

    def enable_dragging(self):
        try:
            self.current_label.bind("<ButtonPress-1>", self.current_label._start_move_handler)
            self.current_label.bind("<B1-Motion>", self.current_label._do_move_handler)
        except Exception:
            pass

    def disable_dragging(self):
        try:
            self.current_label.unbind("<ButtonPress-1>")
            self.current_label.unbind("<B1-Motion>")
        except Exception:
            pass

    def is_mouse_over_overlay(self):
        try:
            x = self.root.winfo_rootx()
            y = self.root.winfo_rooty()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            mx = self.root.winfo_pointerx()
            my = self.root.winfo_pointery()
            return x <= mx <= x + w and y <= my <= y + h
        except Exception:
            return False

    def _set_clickthrough_windows(self, enable: bool):
        # Windows-specific: set WS_EX_TRANSPARENT to let clicks pass through
        try:
            hwnd = self.root.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            LWA_ALPHA = 0x00000002
            if sys.maxsize > 2**32:
                # 64-bit
                set_func = ctypes.windll.user32.SetWindowLongPtrW
                get_func = ctypes.windll.user32.GetWindowLongPtrW
            else:
                set_func = ctypes.windll.user32.SetWindowLongW
                get_func = ctypes.windll.user32.GetWindowLongW

            ex = get_func(hwnd, GWL_EXSTYLE)
            if enable:
                ex |= (WS_EX_LAYERED | WS_EX_TRANSPARENT)
            else:
                ex &= ~(WS_EX_LAYERED | WS_EX_TRANSPARENT)
            set_func(hwnd, GWL_EXSTYLE, ex)

            if enable:
                ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, int(self.opacity * 255), LWA_ALPHA)
        except Exception:
            pass

    def load_config(self):
        load_app_config(self.config_path, self)

    def save_config(self):
        save_app_config(self.config_path, self)

    def apply_theme(self):
        if self.theme == 'light':
            self.bg = '#e2e8f0'
            self.fg = '#0f1720'
            self.accent = '#2563eb'
        else:
            self.bg = '#0f1720'
            self.fg = '#e6eef6'
            self.accent = '#00c2ff'

        self.root.configure(background=self.bg)
        try:
            self.frame.configure(bg=self.bg)
            self.current_label.configure(bg=self.bg, fg=self.fg)
            self.stats_label.configure(bg=self.bg, fg=self.fg)
            self.remote_label.configure(bg=self.bg, fg=self.fg)
            self.segment_label.configure(bg=self.bg, fg=self.fg)
            self.extra_label.configure(bg=self.bg, fg=self.fg)
            self.timer_label.configure(bg=self.bg, fg=self.fg)
            self.graph_canvas.configure(bg=self.bg)
            self.controls.configure(bg=self.bg)
            self.help_label.configure(bg=self.bg, fg=self.fg)
            self.overlay_btn.configure(bg='#334155', fg=self.fg)
            self.settings_btn.configure(bg='#334155', fg=self.fg)
            self.reset_btn.configure(bg='#334155', fg=self.fg)
            self.mini_toggle_btn.configure(bg=self.bg, activebackground=self.bg)
            self.font_scale.configure(bg=self.bg, fg=self.fg)
        except Exception:
            pass

    def apply_obs_mode(self):
        try:
            if self.obs_mode:
                # borderless + transparent background color key
                try:
                    self.root.overrideredirect(True)
                except Exception:
                    pass
                try:
                    self.root.wm_attributes('-transparentcolor', self.bg)
                except Exception:
                    pass
                # enable click-through for capture
                try:
                    self.set_clickthrough(True)
                except Exception:
                    pass
                # resize to OBS friendly ratio (compact)
                try:
                    self.root.geometry(f"{int(self.width)}x{int(self.height)}")
                except Exception:
                    pass
            else:
                try:
                    self.root.overrideredirect(False)
                except Exception:
                    pass
                try:
                    # remove transparent color
                    self.root.wm_attributes('-transparentcolor', '')
                except Exception:
                    pass
                try:
                    self.set_clickthrough(False)
                except Exception:
                    pass
        except Exception:
            pass

    # --- OBS WebSocket integration (simple polling approach) ---
    def start_obs_ws(self):
        if self._obs_thread and self._obs_thread.is_alive():
            return
        self._obs_running = True
        t = threading.Thread(target=self._obs_ws_loop, daemon=True)
        t.start()
        self._obs_thread = t

    def stop_obs_ws(self):
        try:
            self._obs_running = False
            if self._obs_client:
                try:
                    self._obs_client.disconnect()
                except Exception:
                    pass
                self._obs_client = None
        except Exception:
            pass

    def _obs_ws_loop(self):
        try:
            from obswebsocket import obsws, requests
        except Exception:
            print("OBS WebSocket client not available. Install 'obs-websocket-py' or 'obs-websocket' package.")
            self._obs_running = False
            return

        host = self.obs_ws_host or 'localhost'
        port = int(self.obs_ws_port or 4455)
        pw = self.obs_ws_password or ''
        client = None
        last_streaming = None
        while self._obs_running:
            try:
                if client is None:
                    client = obsws(host, port, pw)
                    client.connect()
                    self._obs_client = client
                # Get streaming status
                try:
                    status = client.call(requests.GetStreamingStatus())
                    try:
                        streaming = bool(status.getStreaming())
                    except Exception:
                        try:
                            streaming = bool(status.get('streaming', False))
                        except Exception:
                            streaming = False
                except Exception:
                    streaming = False

                if last_streaming is None:
                    last_streaming = streaming
                if streaming != last_streaming:
                    last_streaming = streaming
                    if streaming:
                        # stream started
                        if self.scene_on_stream_start:
                            try:
                                client.call(requests.SetCurrentScene(self.scene_on_stream_start))
                            except Exception:
                                pass
                        # ensure overlay visible if streamer mode
                        try:
                            if self.streamer_mode:
                                self.overlay_var.set(False)
                                self.toggle_overlay()
                        except Exception:
                            pass
                    else:
                        # stream stopped
                        if self.scene_on_stream_stop:
                            try:
                                client.call(requests.SetCurrentScene(self.scene_on_stream_stop))
                            except Exception:
                                pass
                time.sleep(1)
            except Exception as exc:
                print('OBS WS loop error:', exc)
                try:
                    if client:
                        try:
                            client.disconnect()
                        except Exception:
                            pass
                except Exception:
                    pass
                client = None
                self._obs_client = None
                time.sleep(5)

        try:
            if client:
                try:
                    client.disconnect()
                except Exception:
                    pass
        except Exception:
            pass

    def change_scene(self, scene_name: str):
        try:
            if self._obs_client:
                from obswebsocket import requests
                try:
                    self._obs_client.call(requests.SetCurrentScene(scene_name))
                except Exception:
                    pass
        except Exception:
            pass

    def draw_graph(self, value: float):
        self.apm_history.append(value)
        width = max(10, self.graph_canvas.winfo_width())
        height = max(10, self.graph_canvas.winfo_height())
        values = list(self.apm_history)
        if not values:
            return
        max_val = max(values) or 1
        step = width / max(len(values) - 1, 1)
        points = []
        for index, val in enumerate(values):
            x = index * step
            y = height - (val / max_val) * (height - 4) - 2
            points.extend((x, y))
        self.graph_canvas.delete('all')
        # draw min/max and average lines
        if self.low_apm is not None:
            y_min = height - (self.low_apm / max_val) * (height - 10) - 4
            self.graph_canvas.create_line(0, y_min, width, y_min, fill="#475569", dash=(2, 2))
        y_max = height - (self.high_apm / max_val) * (height - 10) - 4
        self.graph_canvas.create_line(0, y_max, width, y_max, fill="#7dd3fc", dash=(2, 2))
        avg_val = sum(values) / len(values)
        y_avg = height - (avg_val / max_val) * (height - 10) - 4
        self.graph_canvas.create_line(0, y_avg, width, y_avg, fill="#38bdf8", dash=(3, 2))
        if len(points) >= 4:
            self.graph_canvas.create_line(points, fill=self.accent, width=2, smooth=True)
        # current progress bar
        bar_length = int(min(values[-1] / max_val, 1.0) * width)
        self.graph_canvas.create_rectangle(0, height - 8, bar_length, height, fill=self.accent, outline="")
        self.graph_canvas.create_rectangle(0, 0, width, height, outline="#334155")
        self.graph_canvas.create_text(6, 4, anchor='nw', text=f"Trend: {values[-1]:.0f}", fill=self.fg, font=("Consolas", 8))

    def update_segment_labels(self, apm_float, avg):
        best_segment = int(max(self.high_apm, apm_float))
        comparison = "haut" if apm_float > avg else "bas"
        self.segment_label.config(text=f"Best: {best_segment}    Zone: {comparison}")

    def update_gaming_zone(self, apm_float):
        if apm_float >= self.alert_high_threshold:
            self.gaming_zone = 'burst'
        elif apm_float <= self.alert_low_threshold:
            self.gaming_zone = 'calme'
        else:
            self.gaming_zone = 'normal'
        if self.gaming_zone == 'burst':
            self.graph_canvas.configure(bg="#1b2230")
        elif self.gaming_zone == 'calme':
            self.graph_canvas.configure(bg="#102028")
        else:
            self.graph_canvas.configure(bg=self.bg)

    def record_history(self, now, apm, cps, dpm):
        if now - self._last_history_record >= self.history_interval:
            self.history.append({
                'timestamp': now,
                'apm': apm,
                'cps': cps,
                'dpm': dpm,
                'avg': self.compute_average(),
            })
            self._last_history_record = now

    def export_history(self):
        export_history_helper(self.history, self.root)

    def compute_cps(self):
        now = time.time()
        cutoff = now - 1.0
        return sum(1 for event_time in self.events if event_time >= cutoff)

    def reset_stats(self):
        """Reset APM stats and update UI immediately."""
        self.session_count += 1
        self.high_apm = 0
        self.low_apm = None
        self.total_actions = 0
        self.events.clear()
        self.alert_state = None
        self.session_start = time.time()
        self.apm_history.clear()
        self.current_label.config(text="APM: 0")
        self.stats_label.config(text="Avg: 0.0 | Best: 0 | Worst: 0")
        self.summary_label.config(text=f"CPS: 0 | DPM: 0 | Sessions: {self.session_count} | Active: 00:00:00")
        self.remote_label.config(text="Remote: off")
        self.timer_label.config(text="Temps: 00:00:00")
        self.apply_theme()
        self.save_config()

    def toggle_overlay_button(self):
        # Toggle overlay state from a button (keeps overlay_var in sync)
        self.overlay_var.set(not self.overlay_var.get())
        self.toggle_overlay()

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Paramètres APM")
        win.configure(bg=self.bg)
        win.resizable(True, True)
        win.geometry("760x560")
        win.columnconfigure(0, weight=1)
        win.columnconfigure(1, weight=1)

        header = tk.Frame(win, bg=self.bg)
        header.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(header, text="Paramètres", bg=self.bg, fg=self.fg, font=("Consolas", 14, "bold")).pack(anchor="w")
        tk.Label(header, text="Tous les réglages utiles pour l'overlay, les alertes et le stream.", bg=self.bg, fg=self.fg, font=("Consolas", 9)).pack(anchor="w")

        notebook = ttk.Notebook(win)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        overlay_frame = tk.Frame(notebook, bg=self.bg)
        alerts_frame = tk.Frame(notebook, bg=self.bg)
        stream_frame = tk.Frame(notebook, bg=self.bg)
        history_frame = tk.Frame(notebook, bg=self.bg)
        notebook.add(overlay_frame, text="Overlay")
        notebook.add(alerts_frame, text="Alertes")
        notebook.add(stream_frame, text="Stream")
        notebook.add(history_frame, text="Historique")

        # Overlay tab
        tk.Label(overlay_frame, text="Profil :", bg=self.bg, fg=self.fg).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        profile_combo = ttk.Combobox(overlay_frame, values=list(self.profiles.keys()), state="readonly")
        profile_combo.set(self.current_profile)
        profile_combo.grid(row=0, column=1, padx=8, pady=6, sticky="we")

        tk.Label(overlay_frame, text="Opacité:", bg=self.bg, fg=self.fg).grid(row=1, column=0, sticky="w", padx=8, pady=6)
        opacity_scale = tk.Scale(overlay_frame, from_=0.2, to=1.0, resolution=0.02, orient="horizontal",
                                 bg=self.bg, fg=self.fg, troughcolor="#555555", length=300)
        opacity_scale.set(self.opacity)
        opacity_scale.grid(row=1, column=1, padx=8, pady=6, sticky="we")

        tk.Label(overlay_frame, text="Fenêtre smoothing (s):", bg=self.bg, fg=self.fg).grid(row=2, column=0, sticky="w", padx=8, pady=6)
        smooth_scale = tk.Scale(overlay_frame, from_=5, to=180, orient="horizontal", bg=self.bg, fg=self.fg,
                                troughcolor="#555555", length=300)
        smooth_scale.set(int(self.smooth_window))
        smooth_scale.grid(row=2, column=1, padx=8, pady=6, sticky="we")

        tk.Label(overlay_frame, text="Session (s):", bg=self.bg, fg=self.fg).grid(row=3, column=0, sticky="w", padx=8, pady=6)
        session_scale = tk.Scale(overlay_frame, from_=60, to=24*3600, resolution=60, orient="horizontal", bg=self.bg,
                                 fg=self.fg, troughcolor="#555555", length=300)
        session_scale.set(int(self.session_seconds))
        session_scale.grid(row=3, column=1, padx=8, pady=6, sticky="we")

        tk.Label(overlay_frame, text="Thème:", bg=self.bg, fg=self.fg).grid(row=4, column=0, sticky="w", padx=8, pady=6)
        theme_combo = ttk.Combobox(overlay_frame, values=['dark', 'light'], state='readonly')
        theme_combo.set(self.theme)
        theme_combo.grid(row=4, column=1, padx=8, pady=6, sticky='we')

        compact_var = tk.BooleanVar(value=self.compact_mode)
        tk.Checkbutton(overlay_frame, text="Mode compact", variable=compact_var, bg=self.bg, fg=self.fg,
                       selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=5, column=0, columnspan=2,
                                                                                                   sticky="w", padx=8, pady=6)
        start_minimized_var = tk.BooleanVar(value=self.start_minimized)
        tk.Checkbutton(overlay_frame, text="Démarrer réduit", variable=start_minimized_var, bg=self.bg, fg=self.fg,
                       selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=6, column=0, columnspan=2,
                                                                                                   sticky="w", padx=8, pady=6)
        decimals_var = tk.BooleanVar(value=self.show_decimals)
        tk.Checkbutton(overlay_frame, text="Afficher décimales", variable=decimals_var, bg=self.bg, fg=self.fg,
                       selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=7, column=0, columnspan=2,
                                                                                                   sticky="w", padx=8, pady=6)
        remote_var = tk.BooleanVar(value=self.remote_enabled)
        tk.Checkbutton(overlay_frame, text="Stats distantes", variable=remote_var, bg=self.bg, fg=self.fg,
                       selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=8, column=0, columnspan=2,
                                                                                                   sticky="w", padx=8, pady=6)

        tk.Label(overlay_frame, text="URL remote:", bg=self.bg, fg=self.fg).grid(row=9, column=0, sticky="w", padx=8, pady=6)
        remote_entry = tk.Entry(overlay_frame, bg="#1f2937", fg=self.fg, insertbackground=self.fg, width=44)
        remote_entry.insert(0, ";".join(self.remote_urls) if self.remote_urls else self.remote_url)
        remote_entry.grid(row=9, column=1, padx=8, pady=6, sticky="we")

        # Alerts tab
        alert_var = tk.BooleanVar(value=self.alert_enabled)
        tk.Checkbutton(alerts_frame, text="Alertes sonores", variable=alert_var, bg=self.bg, fg=self.fg,
                       selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=0, column=0, columnspan=2,
                                                                                                   sticky="w", padx=8, pady=6)
        tk.Label(alerts_frame, text="Seuil haut APM:", bg=self.bg, fg=self.fg).grid(row=1, column=0, sticky="w", padx=8, pady=6)
        high_thresh = tk.Scale(alerts_frame, from_=60, to=300, orient='horizontal', bg=self.bg, fg=self.fg,
                               troughcolor="#555555", length=300)
        high_thresh.set(self.alert_high_threshold)
        high_thresh.grid(row=1, column=1, padx=8, pady=6, sticky='we')
        tk.Label(alerts_frame, text="Seuil bas APM:", bg=self.bg, fg=self.fg).grid(row=2, column=0, sticky="w", padx=8, pady=6)
        low_thresh = tk.Scale(alerts_frame, from_=0, to=60, orient='horizontal', bg=self.bg, fg=self.fg,
                              troughcolor="#555555", length=300)
        low_thresh.set(self.alert_low_threshold)
        low_thresh.grid(row=2, column=1, padx=8, pady=6, sticky='we')

        # Stream tab
        obs_var = tk.BooleanVar(value=self.obs_mode)
        tk.Checkbutton(stream_frame, text="Mode OBS (transparent)", variable=obs_var, bg=self.bg, fg=self.fg,
                       selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=0, column=0, columnspan=2,
                                                                                                   sticky="w", padx=8, pady=6)
        streamer_var = tk.BooleanVar(value=self.streamer_mode)
        tk.Checkbutton(stream_frame, text="Mode Streamer (persist)", variable=streamer_var, bg=self.bg, fg=self.fg,
                      selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=1, column=0, columnspan=2,
                                                                                                  sticky="w", padx=8, pady=6)
        api_var = tk.BooleanVar(value=self.api_enabled)
        tk.Checkbutton(stream_frame, text="Activer API HTTP locale", variable=api_var, bg=self.bg, fg=self.fg,
                      selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=2, column=0, columnspan=2,
                                                                                                  sticky="w", padx=8, pady=6)
        tk.Label(stream_frame, text="Port API:", bg=self.bg, fg=self.fg).grid(row=3, column=0, sticky="w", padx=8, pady=6)
        api_port_entry = tk.Entry(stream_frame, bg="#1f2937", fg=self.fg, insertbackground=self.fg)
        api_port_entry.insert(0, str(self.api_port))
        api_port_entry.grid(row=3, column=1, padx=8, pady=6, sticky='we')
        obs_ws_var = tk.BooleanVar(value=self.obs_ws_enabled)
        tk.Checkbutton(stream_frame, text="Activer OBS WebSocket", variable=obs_ws_var, bg=self.bg, fg=self.fg,
                      selectcolor=self.bg, activebackground=self.bg, activeforeground=self.fg).grid(row=4, column=0, columnspan=2,
                                                                                                  sticky="w", padx=8, pady=6)
        tk.Label(stream_frame, text="OBS Host:", bg=self.bg, fg=self.fg).grid(row=5, column=0, sticky="w", padx=8, pady=6)
        obs_host_entry = tk.Entry(stream_frame, bg="#1f2937", fg=self.fg, insertbackground=self.fg)
        obs_host_entry.insert(0, str(self.obs_ws_host))
        obs_host_entry.grid(row=5, column=1, padx=8, pady=6, sticky='we')
        tk.Label(stream_frame, text="OBS Port:", bg=self.bg, fg=self.fg).grid(row=6, column=0, sticky="w", padx=8, pady=6)
        obs_port_entry = tk.Entry(stream_frame, bg="#1f2937", fg=self.fg, insertbackground=self.fg)
        obs_port_entry.insert(0, str(self.obs_ws_port))
        obs_port_entry.grid(row=6, column=1, padx=8, pady=6, sticky='we')
        tk.Label(stream_frame, text="OBS Password:", bg=self.bg, fg=self.fg).grid(row=7, column=0, sticky="w", padx=8, pady=6)
        obs_pw_entry = tk.Entry(stream_frame, bg="#1f2937", fg=self.fg, insertbackground=self.fg, show='*')
        obs_pw_entry.insert(0, str(self.obs_ws_password))
        obs_pw_entry.grid(row=7, column=1, padx=8, pady=6, sticky='we')
        tk.Label(stream_frame, text="Scène démarrage stream:", bg=self.bg, fg=self.fg).grid(row=8, column=0, sticky="w", padx=8, pady=6)
        scene_start_entry = tk.Entry(stream_frame, bg="#1f2937", fg=self.fg, insertbackground=self.fg)
        scene_start_entry.insert(0, str(self.scene_on_stream_start))
        scene_start_entry.grid(row=8, column=1, padx=8, pady=6, sticky='we')
        tk.Label(stream_frame, text="Scène arrêt stream:", bg=self.bg, fg=self.fg).grid(row=9, column=0, sticky="w", padx=8, pady=6)
        scene_stop_entry = tk.Entry(stream_frame, bg="#1f2937", fg=self.fg, insertbackground=self.fg)
        scene_stop_entry.insert(0, str(self.scene_on_stream_stop))
        scene_stop_entry.grid(row=9, column=1, padx=8, pady=6, sticky='we')

        # History tab
        tk.Label(history_frame, text="Historique actuel: ", bg=self.bg, fg=self.fg).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        tk.Label(history_frame, text=f"{len(self.history)} entrées", bg=self.bg, fg=self.fg).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        tk.Button(history_frame, text="Exporter CSV", command=self.export_history, bg="#334155", fg=self.fg,
                  relief="flat", bd=0, padx=10, pady=6).grid(row=1, column=0, padx=8, pady=8, sticky="w")
        tk.Button(history_frame, text="Snapshot JSON", command=self.take_snapshot, bg="#334155", fg=self.fg,
                  relief="flat", bd=0, padx=10, pady=6).grid(row=1, column=1, padx=8, pady=8, sticky="w")

        actions = tk.Frame(win, bg=self.bg)
        actions.pack(fill="x", padx=10, pady=(0, 12))

        def fetch_remote_and_close():
            self.fetch_remote_stats(show_popup=True)

        def apply_and_close():
            try:
                self.opacity = float(opacity_scale.get())
                self.smooth_window = float(smooth_scale.get())
                self.session_seconds = int(session_scale.get())
                self.show_decimals = bool(decimals_var.get())
                self.remote_enabled = bool(remote_var.get())
                self.alert_enabled = bool(alert_var.get())
                self.alert_high_threshold = int(high_thresh.get())
                self.alert_low_threshold = int(low_thresh.get())
                self.start_minimized = bool(start_minimized_var.get())
                remote_text = remote_entry.get().strip()
                if remote_text:
                    self.remote_urls = [u.strip() for u in remote_text.split(';') if u.strip()]
                    self.remote_url = self.remote_urls[0] if self.remote_urls else ''
                else:
                    self.remote_urls = []
                    self.remote_url = ''
                self.compact_mode = bool(compact_var.get())
                self.theme = theme_combo.get() or self.theme
                self.current_profile = profile_combo.get() or self.current_profile
                self.obs_mode = bool(obs_var.get())
                self.streamer_mode = bool(streamer_var.get())
                self.obs_ws_enabled = bool(obs_ws_var.get())
                self.obs_ws_host = obs_host_entry.get().strip() or self.obs_ws_host
                try:
                    self.obs_ws_port = int(obs_port_entry.get())
                except Exception:
                    pass
                self.obs_ws_password = obs_pw_entry.get()
                self.scene_on_stream_start = scene_start_entry.get().strip()
                self.scene_on_stream_stop = scene_stop_entry.get().strip()
                was_api = bool(self.api_enabled)
                self.api_enabled = bool(api_var.get())
                try:
                    self.api_port = int(api_port_entry.get())
                except Exception:
                    pass
                if self.current_profile in self.profiles:
                    self.apply_profile(self.current_profile)
                self.apply_theme()
                try:
                    if self.obs_mode:
                        self.apply_obs_mode()
                    else:
                        self.set_clickthrough(self.overlay)
                except Exception:
                    pass
                try:
                    if self.streamer_mode:
                        self.overlay_var.set(False)
                        self.toggle_overlay()
                except Exception:
                    pass
                try:
                    if self.api_enabled and not was_api:
                        self.start_api_server()
                    elif not self.api_enabled and was_api:
                        self.stop_api_server()
                except Exception:
                    pass
                try:
                    self.root.attributes("-alpha", self.opacity)
                except Exception:
                    pass
                self.save_config()
            except Exception:
                pass
            win.destroy()

        tk.Button(actions, text="Appliquer", command=apply_and_close, bg="#334155", fg=self.fg, relief="flat", bd=0, padx=12, pady=8).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Reset stats", command=self.reset_stats, bg="#334155", fg=self.fg, relief="flat", bd=0, padx=12, pady=8).pack(side="left", padx=(0, 8))
        tk.Button(actions, text="Fetch Remote", command=fetch_remote_and_close, bg="#334155", fg=self.fg, relief="flat", bd=0, padx=12, pady=8).pack(side="left")

    def change_font(self, value):
        size = int(float(value))
        self.font_size = size
        self.current_label.configure(font=("Consolas", size, "bold"))

    def quit(self):
        if keyboard and mouse:
            try:
                self.keyboard_listener.stop()
                self.mouse_listener.stop()
            except Exception:
                pass
        self.root.destroy()


if __name__ == "__main__":
    app = APMMonitor()
    app.root.mainloop()
