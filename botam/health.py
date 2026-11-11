"""Tiny HTTP server for Render's health check and the external cron ping."""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

from . import __version__


def start_health_server(port: int, status_provider: Callable[[], dict]) -> ThreadingHTTPServer:
    started = time.time()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, head_only: bool):
            body = json.dumps(
                {"status": "ok", "service": "botam", "version": __version__,
                 "uptime_s": int(time.time() - started), "engines": status_provider()}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head_only:
                self.wfile.write(body)

        def do_GET(self):
            self._send(False)

        def do_HEAD(self):
            self._send(True)

        def log_message(self, *args):  # keep logs clean
            pass

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, name="health", daemon=True).start()
    return server
