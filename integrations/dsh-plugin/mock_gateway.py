#!/usr/bin/env python3
"""Hoshinoumi mock gateway for DSH plugin testing.

This is NOT the real bot backend. It serves the same HTTP shapes the DSH
plugin expects so the plugin can be tested without starting the bot.

Run:
    python integrations/dsh-plugin/mock_gateway.py
    python integrations/dsh-plugin/mock_gateway.py --port 27005 --token mock-token

Then configure the plugin:
    backend address: http://127.0.0.1:27005
    token:           mock-token
    owner QQ:        10001
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "35.2.25.0"
SCHEMA = 35
OWNER_QQ = "10001"

MEMORY = {
    OWNER_QQ: [
        ("昨天方案过了，终于松了口气。", "那很好啊，要不要记进今天值得高兴的事？"),
        ("这个月结余三千三，旅行目标到六成了。", "嗯，离旅行又近了一点。"),
        ("今天外面有点冷。", "先喝点热的吧，别急着出门。"),
    ],
    "10002": [
        ("最近在看的书是《十日终焉》。", "窗边光线好的时候看，会舒服一点。"),
    ],
}

HISTORY = [
    {"id": 1, "role": "assistant", "content": "你回来啦。今天外面有点冷，先喝点热的吧。", "created_at": "2026-11-18 20:58:00"},
    {"id": 2, "role": "user", "content": "刚到家，方案终于过了。", "created_at": "2026-11-18 21:00:00"},
    {"id": 3, "role": "assistant", "content": "那很好啊。要不要记进“今天值得高兴的事”？", "created_at": "2026-11-18 21:01:00"},
    {"id": 4, "role": "assistant", "content": "本月结余 ¥3,300，旅行目标 60% 了。", "created_at": "2026-11-18 21:03:00"},
    {"id": 5, "role": "user", "content": "早。今天有什么安排？", "created_at": "2026-11-19 09:12:00"},
    {"id": 6, "role": "assistant", "content": "上午看书，下午把房间收拾一下。你忙你的，我在。", "created_at": "2026-11-19 09:13:00"},
]

LOGS = [
    "2026-11-19 09:13:00 INFO  chat target=10001 len=18",
    "2026-11-19 09:12:00 INFO  command status",
    "2026-11-19 09:04:00 WARN  search_images upstream timeout, no retry",
    "2026-11-19 08:58:00 INFO  memory append target=10001",
    "2026-11-19 08:40:00 INFO  scheduler tick tasks=3",
]

TASKS = [
    {"id": 1, "schedule_type": "daily", "content": "每日早报", "at_time": "08:00", "enabled": True, "next_ts": "2026-11-20 08:00:00"},
    {"id": 2, "schedule_type": "daily", "content": "日记提醒", "at_time": "22:30", "enabled": True, "next_ts": "2026-11-19 22:30:00"},
    {"id": 3, "schedule_type": "hourly", "content": "健康检查", "at_time": "每小时", "enabled": False, "next_ts": None},
]

PLAN = {
    "week_start": "2026-11-16",
    "days": [
        {"date": "2026-11-16", "items": [{"text": "读书 30 分钟", "done": True}]},
        {"date": "2026-11-17", "items": [{"text": "整理笔记", "done": False}]},
    ],
}

PERSONAS = [
    {"name": "nao", "active": True,
     "files": {"prompt": True, "life": True, "supplement": True, "state": True, "voice": True},
     "prompt_excerpt": "你是友利奈绪(Charlotte)，15岁傲娇毒舌学生会会长。",
     "state": {"mood": 0.1, "energy": 0.7, "lonely": 0.15},
     "voice": {"voice": "zh-CN-XiaoxiaoNeural"},
     "prompt": "你是友利奈绪(Charlotte)。", "supplement": "mock supplement", "life": "mock life"},
]

SAVINGS = {
    "total_cents": 330000,
    "accounts": [{"account": "银行卡", "balance_cents": 330000}],
    "entries": [
        {"id": 2, "account": "银行卡", "kind": "income", "amount_cents": 800000, "category": "工资", "note": "mock", "occurred_at": "2026-11-01 09:00:00", "source": "manual"},
        {"id": 1, "account": "银行卡", "kind": "expense", "amount_cents": -470000, "category": "生活", "note": "mock", "occurred_at": "2026-11-02 12:00:00", "source": "manual"},
    ],
}

WEEKLY = {
    3: [
        {"name": "大学物理实验C9903班", "teacher": "5106.罗水平", "location": "未定", "weekday": 1, "weekday_name": "星期一", "period_start": 1, "period_end": 2, "weeks_raw": "3-5,7(未定)", "weeks": [3, 4, 5, 7], "start_week": 3, "end_week": 7, "source": "jwc_html"},
        {"name": "大学英语Ⅲ0203班", "teacher": "4930.徐小芳", "location": "5-628（南楼）", "weekday": 1, "weekday_name": "星期一", "period_start": 3, "period_end": 4, "weeks_raw": "3-17(5-628（南楼）)", "weeks": list(range(3, 18)), "start_week": 3, "end_week": 17, "source": "jwc_html"},
    ]
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Handler(BaseHTTPRequestHandler):
    server_version = "HoshinoumiMock/" + VERSION
    token = "mock-token"

    def log_message(self, fmt, *args):
        print(f"[mock] {self.address_string()} {fmt % args}")

    def _send(self, status: int, data, content_type="application/json; charset=utf-8"):
        if isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data):
        self._send(status, data)

    def _authorized(self) -> bool:
        if not self.token:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {self.token}"

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", "0") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "authorization,content-type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        q = parse_qs(u.query)

        if path in ("/healthz", "/api/health"):
            self._json(200, {"status": "ok", "mock": True, "version": VERSION, "time": _now()})
            return
        if path == "/readyz":
            self._json(200, {"ok": True, "ready": True, "schema": SCHEMA, "version": VERSION, "mock": True})
            return
        if path.startswith("/internal/"):
            return self._internal_get(path, q)
        if not self._authorized():
            self._json(401, {"error": "unauthorized", "message": "bad token"})
            return

        if path == "/api/status":
            self._json(200, {
                "status": "running",
                "mock": True,
                "master_qq": OWNER_QQ,
                "deepseek": True,
                "doubao": False,
                "clip": False,
                "sticker_api": False,
                "stats": {"images": 12, "memories": 4, "events": 7, "logs": len(LOGS), "keywords": 9, "ai_responses": 21},
                "runtime": {"dialogue_targets": len(MEMORY), "global_keywords": 9, "stickers": 0, "daily_triggers": 2},
            })
            return
        if path == "/api/conversations":
            rows = []
            for tid, items in MEMORY.items():
                rows.append({
                    "target_id": tid,
                    "name": "测试私聊" if tid == OWNER_QQ else "测试群 " + tid,
                    "type": "private" if tid == OWNER_QQ else "group",
                    "count": len(items),
                    "last_message": items[-1][0][:40] if items else "",
                    "updated_at": "2026-11-19 21:04:00",
                })
            self._json(200, {"ok": True, "data": rows, "mock": True})
            return
        if path == "/api/history":
            target = (q.get("target_id") or [OWNER_QQ])[0]
            limit = int((q.get("limit") or ["100"])[0])
            self._json(200, {"ok": True, "target_id": target, "data": HISTORY[-max(1, min(limit, 100)):], "mock": True})
            return
        if path == "/api/state":
            self._json(200, {"ok": True, "data": {"mood": 0.1, "energy": 0.7, "lonely": 0.15, "emotion": "平静"}, "mock": True})
            return
        if path == "/api/presence":
            self._json(200, {"activity": "看书", "detail": "窗边", "idle_min": 0, "mock": True})
            return
        if path == "/api/cron":
            self._json(200, {"ok": True, "data": TASKS, "mock": True})
            return
        if path == "/api/commands":
            data = [
                {"name": "!help", "group": "基础", "help": "命令帮助", "owner": False},
                {"name": "!status", "group": "基础", "help": "运行状态", "owner": False},
                {"name": "!memory", "group": "记忆", "help": "记忆查询", "owner": False},
                {"name": "!savings", "group": "日常", "help": "存钱统计", "owner": False},
                {"name": "!persona", "group": "配置", "help": "人设", "owner": False},
                {"name": "!cron", "group": "日常", "help": "定时任务", "owner": False},
            ]
            self._json(200, {"ok": True, "count": len(data), "data": data, "mock": True})
            return
        if path == "/api/memory":
            target = (q.get("target_id") or [""])[0]
            if target:
                records = [{"user": u, "bot": b} for u, b in MEMORY.get(target, [])]
                self._json(200, {"target_id": target, "count": len(records), "records": records, "mock": True})
            else:
                targets = [
                    {"target_id": tid, "count": len(items), "last_message": items[-1][0][:30] if items else ""}
                    for tid, items in MEMORY.items()
                ]
                self._json(200, {"total_targets": len(targets), "targets": targets, "mock": True})
            return
        if path == "/api/logs":
            limit = int((q.get("limit") or ["20"])[0])
            self._json(200, {"count": min(limit, len(LOGS)), "logs": LOGS[: max(1, limit)], "mock": True})
            return
        if path == "/api/plan":
            self._json(200, PLAN)
            return
        if path == "/api/usage":
            self._json(200, {"records": [], "summary": {"total_prompt_tokens": 0, "total_completion_tokens": 0, "total_tokens": 0, "count": 0}, "mock": True})
            return
        if path == "/api/persona":
            name = (q.get("name") or [""])[0]
            if name:
                item = next((x for x in PERSONAS if x["name"] == name), None)
                self._json(200 if item else 404, {"ok": bool(item), "data": item, "active": "nao"})
            else:
                self._json(200, {"ok": True, "data": PERSONAS, "active": "nao", "count": len(PERSONAS)})
            return
        if path == "/api/persona/export":
            name = (q.get("name") or [""])[0]
            item = next((x for x in PERSONAS if x["name"] == name), None)
            self._json(200 if item else 404, {"ok": bool(item), "data": item})
            return
        if path == "/api/savings":
            self._json(200, {"ok": True, **SAVINGS, "mock": True})
            return
        if path == "/api/savings/events":
            self._json(200, {"ok": True, "events": [{"id": 1, "summary": "旅行计划", "created_at": "2026-11-01"}], "mock": True})
            return
        if path == "/api/balance":
            self._json(200, {"ok": True, "is_available": True, "balance_infos": [{"currency": "CNY", "total_balance": "42.00", "granted_balance": "2.00", "topped_up_balance": "40.00"}], "fetched_at": _now(), "mock": True})
            return
        if path == "/api/relation":
            tid = (q.get("target_id") or [OWNER_QQ])[0]
            if tid == OWNER_QQ:
                aff, tier, desc = 0.62, "熟", "算是熟人：可以开玩笑，但别太热络"
            else:
                aff, tier, desc = 0.18, "认识", "只是认识：礼貌、有距离，不主动交底"
            self._json(200, {"ok": True, "target_id": tid, "affinity": aff, "tier": tier, "description": desc, "events": [{"delta": 0.02 if tid == OWNER_QQ else -0.01, "reason": "聊天", "severity": "minor", "created_at": "2026-11-19 12:00:00"}], "mock": True})
            return
        if path == "/api/weekly-plan":
            week = int((q.get("week") or ["1"])[0])
            rows = WEEKLY.get(week, [])
            self._json(200, {"ok": True, "week": week, "courses": rows, "count": len(rows), "mock": True})
            return
        if path == "/api/token":
            self._json(200, {"token_prefix": "mock...", "host": "127.0.0.1", "port": self.server.server_port, "mock": True})
            return
        self._json(404, {"error": "not_found", "path": path})

    def _internal_get(self, path, q):
        if path == "/internal/history":
            target = (q.get("target_id") or [OWNER_QQ])[0]
            limit = int((q.get("limit") or ["30"])[0])
            rows = HISTORY[-max(1, min(limit, 100)):]
            self._json(200, {"ok": True, "data": rows, "target_id": target, "mock": True})
            return
        if path == "/internal/cron":
            self._json(200, {"ok": True, "data": TASKS, "mock": True})
            return
        self._json(404, {"error": "not_found", "path": path})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        if path.startswith("/internal/"):
            self._json(404, {"error": "not_found", "path": path})
            return
        if not self._authorized():
            self._json(401, {"error": "unauthorized", "message": "bad token"})
            return

        if path == "/api/persona/import":
            data = body.get("data") if isinstance(body.get("data"), dict) else body
            name = str(data.get("name") or "").strip()
            if not name or not data.get("prompt"):
                self._json(400, {"ok": False, "error": "prompt_required"})
                return
            item = next((x for x in PERSONAS if x["name"] == name), None)
            if item and not body.get("overwrite"):
                self._json(409, {"ok": False, "error": "exists"})
                return
            if item is None:
                item = {"name": name, "files": {"prompt": True, "life": False, "supplement": False, "state": False, "voice": False}, "prompt_excerpt": str(data.get("prompt"))[:160], "state": data.get("state"), "voice": data.get("voice"), "active": False}
                PERSONAS.append(item)
            item["prompt"] = str(data.get("prompt"))
            item["prompt_excerpt"] = item["prompt"][:160]
            self._json(200, {"ok": True, "data": item, "mock": True})
            return
        if path == "/api/persona/activate":
            name = str(body.get("name") or "")
            for x in PERSONAS:
                x["active"] = x["name"] == name
            self._json(200 if any(x["name"] == name for x in PERSONAS) else 404, {"ok": True, "active": name})
            return
        if path == "/api/savings/entries":
            amount = int(round(float(body.get("amount") or 0) * 100))
            kind = str(body.get("kind") or "expense")
            signed = amount if kind == "income" else -abs(amount)
            SAVINGS["entries"].insert(0, {"id": len(SAVINGS["entries"]) + 1, "account": str(body.get("account") or "银行卡"), "kind": kind, "amount_cents": signed, "category": "", "note": str(body.get("note") or ""), "occurred_at": str(body.get("date") or _now()), "source": "manual", "event_id": body.get("event_id"), "ai_visible": bool(body.get("ai_visible", True))})
            SAVINGS["total_cents"] = sum(int(x.get("amount_cents") or 0) for x in SAVINGS["entries"])
            SAVINGS["accounts"] = [{"account": "银行卡", "balance_cents": SAVINGS["total_cents"]}]
            self._json(200, {"ok": True, "id": len(SAVINGS["entries"]), "event_id": body.get("event_id"), "ai_visible": bool(body.get("ai_visible", True)), "mock": True})
            return
        if path == "/api/savings/import":
            rows = body.get("rows") or []
            if body.get("dry_run"):
                self._json(200, {"ok": True, "dry_run": True, "rows": len(rows), "new": len(rows), "duplicates": 0, "preview": rows[:50]})
                return
            self._json(200, {"ok": True, "batch_id": "mock", "rows": len(rows), "inserted": len(rows), "duplicates": 0, "mock": True})
            return
        if path == "/api/weekly-plan":
            week = int(body.get("week") or 1)
            WEEKLY[week] = body.get("courses") or []
            self._json(200, {"ok": True, "week": week, "count": len(WEEKLY[week]), "mock": True})
            return
        if path == "/api/weekly-plan/import":
            week = int(body.get("week") or 1)
            rows = WEEKLY.get(week, [])
            total = len(rows)
            try:
                from pathlib import Path as _Path
                sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
                from bot.life.weekly_plan import parse_html
                parsed = parse_html(str(body.get("html") or ""))
                total = len(parsed)
                rows = [x for x in parsed if not x["weeks"] or week in x["weeks"]]
            except Exception:
                pass
            if not body.get("dry_run"):
                WEEKLY[week] = rows
            self._json(200, {"ok": True, "week": week, "count": len(rows), "all_weeks_count": total, "dry_run": bool(body.get("dry_run")), "courses": rows[:100], "mock": True})
            return
        if path == "/api/chat":
            message = str(body.get("message", "")).strip()
            target = str(body.get("target_id", OWNER_QQ))
            image = str(body.get("image", "")).strip()
            if not message and not image:
                self._json(400, {"error": "empty_message", "message": "message/image is empty"})
                return
            if image:
                reply = "收到一张图片（mock）。"
                HISTORY.append({"id": len(HISTORY) + 1, "role": "user", "content": message or "[图片]", "image_url": image, "created_at": _now()})
                HISTORY.append({"id": len(HISTORY) + 1, "role": "assistant", "content": reply, "created_at": _now()})
                self._json(200, {"reply": reply, "target_id": target, "mock": True, "time": _now()})
                return
            reply = {
                "你好": "你好呀。",
                "在吗": "在的，你说。",
                "存钱": "本月结余 ¥3,300，旅行目标 60%。",
                "书": "我在看《十日终焉》，窗边光线刚好。",
            }.get(message, f"收到：{message}（mock 网关）")
            self._json(200, {"reply": reply, "target_id": target, "mock": True, "time": _now()})
            return
        if path == "/api/command":
            cmd = str(body.get("command", "")).strip().lower()
            if cmd == "status":
                result = f"运行中（mock）\n主人 QQ：{OWNER_QQ}\n记忆：4 条\nschema：{SCHEMA}"
            elif cmd == "help":
                result = "mock 命令目录：status / help / memory / logs"
            elif cmd == "memory":
                result = "10001：3 条记忆"
            else:
                self._json(400, {"error": "unknown_command", "message": f"未知命令: {cmd}"})
                return
            self._json(200, {"success": True, "command": cmd, "result": result, "mock": True})
            return
        self._json(404, {"error": "not_found", "path": path})


class MockServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(port: int = 27005, host: str = "127.0.0.1", token: str = "mock-token") -> MockServer:
    Handler.token = token
    server = MockServer((host, port), Handler)
    return server


def main():
    parser = argparse.ArgumentParser(description="Hoshinoumi mock gateway")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=27005)
    parser.add_argument("--token", default="mock-token", help="Bearer token; empty disables auth")
    args = parser.parse_args()
    server = serve(args.port, args.host, args.token)
    print(f"Hoshinoumi mock gateway: http://{args.host}:{server.server_port}")
    print(f"token: {args.token or '(disabled)'}  owner QQ: {OWNER_QQ}")
    print("This is mock data, not the real bot backend.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
