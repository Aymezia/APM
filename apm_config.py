import json
import os


def load_config(config_path, monitor):
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            monitor.opacity = float(data.get('opacity', monitor.opacity))
            monitor.smooth_window = float(data.get('smooth_window', monitor.smooth_window))
            monitor.session_seconds = int(data.get('session_seconds', monitor.session_seconds))
            monitor.show_decimals = bool(data.get('show_decimals', monitor.show_decimals))
            monitor.remote_enabled = bool(data.get('remote_enabled', monitor.remote_enabled))
            monitor.current_profile = data.get('current_profile', monitor.current_profile)
            monitor.compact_mode = bool(data.get('compact_mode', monitor.compact_mode))
            monitor.mini_mode = bool(data.get('mini_mode', monitor.mini_mode))
            monitor.focus_mode = bool(data.get('focus_mode', monitor.focus_mode))
            monitor.paused = bool(data.get('paused', monitor.paused))
            monitor.session_count = int(data.get('session_count', monitor.session_count))
            monitor.total_active_seconds = int(data.get('total_active_seconds', monitor.total_active_seconds))
            monitor.start_minimized = bool(data.get('start_minimized', monitor.start_minimized))
            monitor.alert_enabled = bool(data.get('alert_enabled', monitor.alert_enabled))
            monitor.alert_high_threshold = int(data.get('alert_high_threshold', monitor.alert_high_threshold))
            monitor.alert_low_threshold = int(data.get('alert_low_threshold', monitor.alert_low_threshold))
            monitor.remote_urls = data.get('remote_urls', monitor.remote_urls) or monitor.remote_urls
            if not monitor.remote_url and monitor.remote_urls:
                monitor.remote_url = monitor.remote_urls[0]
            monitor.theme = data.get('theme', monitor.theme)
            monitor.obs_ws_enabled = bool(data.get('obs_ws_enabled', monitor.obs_ws_enabled))
            monitor.obs_ws_host = data.get('obs_ws_host', monitor.obs_ws_host)
            try:
                monitor.obs_ws_port = int(data.get('obs_ws_port', monitor.obs_ws_port))
            except Exception:
                pass
            monitor.obs_ws_password = data.get('obs_ws_password', monitor.obs_ws_password)
            monitor.scene_on_stream_start = data.get('scene_on_stream_start', monitor.scene_on_stream_start)
            monitor.scene_on_stream_stop = data.get('scene_on_stream_stop', monitor.scene_on_stream_stop)
            return data
    except Exception:
        return {}


def save_config(config_path, monitor):
    try:
        data = {
            'opacity': monitor.opacity,
            'smooth_window': monitor.smooth_window,
            'session_seconds': monitor.session_seconds,
            'show_decimals': monitor.show_decimals,
            'compact_mode': monitor.compact_mode,
            'mini_mode': monitor.mini_mode,
            'focus_mode': monitor.focus_mode,
            'paused': monitor.paused,
            'session_count': monitor.session_count,
            'total_active_seconds': monitor.total_active_seconds,
            'theme': monitor.theme,
            'remote_enabled': monitor.remote_enabled,
            'remote_urls': monitor.remote_urls,
            'current_profile': monitor.current_profile,
            'start_minimized': monitor.start_minimized,
            'alert_enabled': monitor.alert_enabled,
            'alert_high_threshold': monitor.alert_high_threshold,
            'alert_low_threshold': monitor.alert_low_threshold,
            'obs_ws_enabled': monitor.obs_ws_enabled,
            'obs_ws_host': monitor.obs_ws_host,
            'obs_ws_port': monitor.obs_ws_port,
            'obs_ws_password': monitor.obs_ws_password,
            'scene_on_stream_start': monitor.scene_on_stream_start,
            'scene_on_stream_stop': monitor.scene_on_stream_stop,
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
