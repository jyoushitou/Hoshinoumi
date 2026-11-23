#!/usr/bin/env python3
"""v35 local mock backend — UI development only.

Run: python scripts/mock_backend.py --port 27005
No database, no NapCat, no real token verification.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

CONVS = [
    {"target_id": "10001", "name": "奈绪", "type": "private", "member_count": 0,
     "last_message": "你回来啦。今天外面有点冷，先喝点热的吧。", "updated_at": "2026-11-23 08:00:00", "unread": 2},
    {"target_id": "20001", "name": "星之海学生会", "type": "group", "member_count": 3,
     "last_message": "友利：下午的会议改到三点。", "updated_at": "2026-11-23 07:40:00", "unread": 0},
]
MESSAGES = {
    "10001": [
        {"id": 1, "role": "assistant", "content": "你回来啦。今天外面有点冷，先喝点热的吧。", "created_at": "2026-11-23 08:00:00"},
        {"id": 2, "role": "user", "content": "嗯，今天有什么安排？", "created_at": "2026-11-23 08:01:00"},
    ],
    "20001": [
        {"id": 1, "role": "assistant", "content": "友利：下午的会议改到三点。", "created_at": "2026-11-23 07:40:00"},
    ],
}
COUNTER = {"10001": 2, "20001": 1}

def conv(target: str):
    for c in CONVS:
        if c["target_id"] == target:
            return c
    return None

class Handler(BaseHTTPRequestHandler):
    server_version = "HoshinoumiMock/35"

    def log_message(self, fmt, *args):
        print("[mock]", fmt % args, flush=True)

    def _send(self, obj, status=200):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "authorization, content-type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get("content-length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self._send({"ok": True})

    def do_GET(self):
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)
        if path == "/healthz":
            return self._send({"status": "ok", "timestamp": datetime.now().isoformat(timespec="seconds")})
        if path == "/readyz":
            return self._send({"status": "ready"})
        if path == "/api/status":
            return self._send({
                "status": "running", "version": "mock-35.8", "schema": "35",
                "self_qq": "10001", "master_qq": "10001", "deepseek": False,
                "doubao": False, "clip": False, "sticker_api": False,
                "stats": {"images": 0, "memories": 2, "events": 0, "logs": 0, "keywords": 0, "ai_responses": 0},
                "runtime": {"dialogue_targets": 1, "global_keywords": 0, "stickers": 0, "daily_triggers": 0},
                "mock": True,
            })
        if path == "/api/conversations":
            return self._send({"ok": True, "data": CONVS})
        if path == "/api/history":
            target = (q.get("target_id") or [""])[0]
            after = int((q.get("after_seq") or ["0"])[0] or 0)
            rows = [m for m in MESSAGES.get(target, []) if int(m["id"]) > after]
            return self._send({"ok": True, "data": rows, "next_seq": COUNTER.get(target, 0), "has_more": False})
        if path == "/api/persona":
            return self._send({"ok": True, "data": [{"name": "奈绪", "active": True, "title": "默认人设", "mock": True}]})
        if path == "/api/relation":
            return self._send({"ok": True, "tier": "熟悉", "score": 45, "events": [], "mock": True})
        if path == "/api/state":
            return self._send({"ok": True, "data": {"mood": "平静", "energy": 0.7, "loneliness": 0.15, "doing": "未知", "mock": True}})
        if path == "/api/presence":
            return self._send({"ok": True, "online": True, "status": "在线", "mock": True})
        if path == "/api/memory":
            return self._send({"ok": True, "targets": []})
        if path == "/api/savings":
            return self._send({"ok": True, "data": {"total": 12100, "available": 2700, "frozen": 4100, "fixed": 3000, "goals": [], "accounts": [], "mock": True}})
        if path == "/api/weekly-plan":
            return self._send({"ok": True, "week": int((q.get("week") or ["0"])[0] or 0), "courses": []})
        return self._send({"ok": True, "data": [], "mock": True})

    def do_POST(self):
        u = urlparse(self.path)
        path = u.path
        body = self._body()
        if path == "/api/chat":
            target = str(body.get("target_id") or "10001")
            text = str(body.get("message") or "").strip()
            COUNTER[target] = COUNTER.get(target, 0) + 1
            MESSAGES.setdefault(target, []).append({
                "id": COUNTER[target], "role": "user", "content": text,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            COUNTER[target] += 1
            reply = "收到。这是 mock 后端的回复。"
            MESSAGES[target].append({
                "id": COUNTER[target], "role": "assistant", "content": reply,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            if conv(target):
                conv(target)["last_message"] = text or reply
                conv(target)["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return self._send({"success": True, "reply": reply, "mock": True})
        if path == "/api/read":
            return self._send({"ok": True})
        if path == "/api/weekly-plan":
            return self._send({"ok": True, "courses": body.get("courses", []) if isinstance(body, dict) else []})
        if path == "/api/messages" or path.startswith("/api/messages/"):
            return self._send({"ok": True})
        return self._send({"ok": True, "mock": True})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=27005)
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"mock backend listening http://{args.host}:{args.port}", flush=True)
    srv.serve_forever()

if __name__ == "__main__":
    main()
