import json
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs


class StatsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/stats':
            self.send_json(self.server.app_monitor.get_stats_payload())
        elif parsed.path == '/overlay':
            self.send_html(self.server.app_monitor.get_overlay_html())
        else:
            self.send_text('OK', 200)

    def log_message(self, format, *args):
        return

    def send_json(self, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, status=200):
        body = text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class StreamingServer(HTTPServer):
    def __init__(self, server_address, handler_class, app_monitor):
        super().__init__(server_address, handler_class)
        self.app_monitor = app_monitor


def start_api_server(monitor):
    if getattr(monitor, 'api_server', None) is not None:
        stop_api_server(monitor)
    port = monitor.api_port
    try:
        monitor.api_server = StreamingServer(('127.0.0.1', port), StatsHandler, monitor)
        monitor.api_thread = threading.Thread(target=monitor.api_server.serve_forever, daemon=True)
        monitor.api_thread.start()
        monitor.api_running = True
    except OSError:
        monitor.api_running = False


def stop_api_server(monitor):
    try:
        if getattr(monitor, 'api_server', None) is not None:
            monitor.api_server.shutdown()
            monitor.api_server.server_close()
            monitor.api_server = None
    except Exception:
        pass
    monitor.api_running = False


def open_overlay_in_browser(monitor):
    try:
        webbrowser.open(f'http://127.0.0.1:{monitor.api_port}/overlay')
    except Exception:
        pass
