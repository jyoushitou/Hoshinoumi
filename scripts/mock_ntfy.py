#!/usr/bin/env python3
"""极小 ntfy 兼容开发桩，仅用于本机联调 App 的 SSE/通知链路。

生产仍应使用真正的 ntfy server；本文件只实现：
  GET  /v1/health
  GET  /<topic>/sse
  POST /<topic>       (Title / Click headers + text body)

Run:
  .venv\\Scripts\\python.exe scripts\\mock_ntfy.py --port 2586
"""
from __future__ import annotations

import argparse
import json
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOPICS: dict[str, list[queue.Queue]] = {}
LOCK = threading.Lock()


def publish(topic: str, body: str, title: str = "", click: str = "") -> int:
    item = {
        "id": f"mock-{int(time.time() * 1000)}",
        "time": int(time.time()),
        "event": "message",
        "topic": topic,
        "message": body,
        "title": title,
        "click": click,
    }
    with LOCK:
        queues = list(TOPICS.get(topic, []))
    for q in queues:
        q.put(item)
    print(f"[ntfy-mock] publish topic={topic} subscribers={len(queues)} title={title!r} body={body!r}", flush=True)
    return len(queues)


class Handler(BaseHTTPRequestHandler):
    server_version = "HoshinoumiNtfyStub/0.1"

    def log_message(self, fmt, *args):
        print(f"[ntfy-mock] {self.address_string()} {fmt % args}", flush=True)

    def _headers(self, status=200, content_type="text/plain; charset=utf-8", extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.strip("/")
        if path == "v1/health":
            self._headers(content_type="application/json")
            self.wfile.write(b'{"healthy":true}')
            return
        if path.endswith("/sse"):
            topic = path[: -len("/sse")].strip("/")
            if not topic:
                self._headers(400)
                return
            q: queue.Queue = queue.Queue()
            with LOCK:
                TOPICS.setdefault(topic, []).append(q)
            self._headers(200, "text/event-stream", {"Connection": "keep-alive", "X-Accel-Buffering": "no"})
            try:
                self.wfile.write(b": connected\n\n")
                self.wfile.flush()
                while True:
                    try:
                        item = q.get(timeout=20)
                        payload = json.dumps(item, ensure_ascii=False).encode("utf-8")
                        self.wfile.write(b"data: " + payload + b"\n\n")
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with LOCK:
                    if q in TOPICS.get(topic, []):
                        TOPICS[topic].remove(q)
            return
        self._headers(404)

    def do_POST(self):
        path = urlparse(self.path).path.strip("/")
        if not path:
            self._headers(400)
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        publish(path, body, self.headers.get("Title", ""), self.headers.get("Click", ""))
        self._headers(content_type="application/json")
        self.wfile.write(b'{"id":"mock","status":200}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=2586)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print(f"[ntfy-mock] listening on 0.0.0.0:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
