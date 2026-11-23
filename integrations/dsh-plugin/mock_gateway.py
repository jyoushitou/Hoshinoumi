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
import uuid
import os
import base64
import struct
import zlib
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "35.2.25.0"
SCHEMA = 35
OWNER_QQ = "10001"
READS = {}  # target_id -> last_read_id
CUSTOM_GROUPS = {}
GROUP_META = {}
PUSH_DEVICES = {}  # id -> device
PUSH_PREFS = {"messages": True, "reminders": True, "dnd": False}
PUSH_OUTBOX = {}  # id -> notification job
PUSH_TIMERS = {}  # device_id -> timer
AUTH_USERS = {OWNER_QQ: {"password": "mock1234", "token": "mock-token"}}
AUTH_TOKENS = {"mock-token"}
SETUP_CODES = {"HSHM-2026": False}


def _publish_chat(target: str, reply: str) -> None:
    if not PUSH_PREFS.get("messages", True) or PUSH_PREFS.get("dnd"):
        return
    click = f"/chat?target={target}"
    for device in list(PUSH_DEVICES.values()):
        if device.get("revoked_at"):
            continue
        endpoint = str(device.get("endpoint") or "")
        if not endpoint:
            continue
        status = "failed"
        attempts = 1
        try:
            req = urllib.request.Request(endpoint, data=reply.encode("utf-8"), method="POST")
            req.add_header("Title", "Hoshinoumi")
            req.add_header("Click", click)
            req.add_header("Content-Type", "text/plain; charset=utf-8")
            with urllib.request.urlopen(req, timeout=8) as response:
                if 200 <= response.status < 300:
                    status = "sent"
                    attempts = 1
        except Exception as exc:
            print(f"[mock] chat push failed to {endpoint}: {exc}", flush=True)
        oid = uuid.uuid4().hex[:12]
        PUSH_OUTBOX[oid] = {
            "id": oid,
            "user_id": OWNER_QQ,
            "device_id": device["id"],
            "kind": "message",
            "title": "新消息",
            "body": reply,
            "deep_link": click,
            "dedupe_key": "",
            "status": status,
            "attempts": attempts,
            "next_at": _now(),
            "created_at": _now(),
        }


def _schedule_test_push(device, target: str = OWNER_QQ):
    delay = int(os.environ.get("HOSHINOUMI_PUSH_TEST_DELAY", "300"))
    endpoint = str(device.get("endpoint") or "")
    if not endpoint:
        return

    def send():
        try:
            body = "This is a 5-minute test notification".encode("utf-8")
            req = urllib.request.Request(endpoint, data=body, method="POST")
            req.add_header("Title", "Hoshinoumi Test")
            req.add_header("Click", f"/chat?target={target}")
            req.add_header("Content-Type", "text/plain; charset=utf-8")
            with urllib.request.urlopen(req, timeout=10) as response:
                print(f"[mock] test push sent to {endpoint}: HTTP {response.status}", flush=True)
        except Exception as exc:
            print(f"[mock] test push failed to {endpoint}: {exc}", flush=True)

    timer = threading.Timer(max(1, delay), send)
    timer.daemon = True
    timer.start()
    PUSH_TIMERS[device["id"]] = timer

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

GROUP_HISTORY = [
    {"id": 1001, "role": "user", "content": "群里的大家晚上好。", "created_at": "2026-11-19 20:30:00"},
    {"id": 1002, "role": "assistant", "content": "晚上好，今天群里安静得有点过分。", "created_at": "2026-11-19 20:31:00"},
]


def _history(target):
    key = str(target)
    if key in CUSTOM_GROUPS:
        return CUSTOM_GROUPS[key]
    return HISTORY if key in ("", OWNER_QQ) else (GROUP_HISTORY if key == "10002" else [])

def _all_history():
    return list(HISTORY) + list(GROUP_HISTORY)

LOGS = [
    "2026-11-19 09:13:00 INFO  chat target=10001 len=18",
    "2026-11-19 09:12:00 INFO  command status",
    "2026-11-19 09:04:00 WARN  search_images upstream timeout, no retry",
    "2026-11-19 08:58:00 INFO  memory append target=10001",
    "2026-11-19 08:40:00 INFO  scheduler tick tasks=3",
]


COMMAND_CATALOG = [
    ("!help", "基础", "命令帮助", False), ("!ping", "基础", "连通性测试", False), ("!status", "基础", "运行状态", False),
    ("!version", "基础", "版本信息", False), ("!uptime", "基础", "运行时长", False), ("!meta", "基础", "实例元信息", False),
    ("!usage", "基础", "模型用量", False), ("!log", "基础", "最近日志", False), ("!db", "基础", "数据库状态", False),
    ("!stats", "基础", "运行统计", False), ("!history", "基础", "历史记录", False), ("!reload", "基础", "重载配置", True),
    ("!set", "基础", "修改配置", True), ("!exit", "基础", "退出实例", True), ("!quit", "基础", "退出实例", True),
    ("!memory", "记忆", "记忆查询", False), ("!memorybook", "记忆", "记忆本", False), ("!event", "记忆", "事件列表", False),
    ("!keywords", "记忆", "关键词", False), ("!clear", "记忆", "清空记忆", True), ("!profile", "记忆", "画像摘要", False),
    ("!growth", "记忆", "成长记录", False), ("!relation", "记忆", "关系状态", False),
    ("!img", "媒体", "搜图", False), ("!acg", "媒体", "二次元图", False), ("!sticker", "媒体", "表情包", False),
    ("!clip", "媒体", "视频片段", False), ("!voice", "媒体", "语音", False), ("!vision", "媒体", "识图", False),
    ("!say", "媒体", "主动发言", True), ("!sayg", "媒体", "群内发言", True),
    ("!diary", "日常", "日记", False), ("!todo", "日常", "待办", False), ("!cron", "日常", "定时任务", False),
    ("!hooks", "日常", "钩子", False), ("!backup", "日常", "备份", True), ("!update", "日常", "更新", False), ("!task", "日常", "任务", False),
    ("!books", "阅读", "书架", False), ("!book", "阅读", "当前阅读", False),
    ("!plan", "计划", "计划表", False),
    ("!plugin", "插件", "插件管理", True),
    ("!adduser", "账号", "添加用户", True), ("!persona", "账号", "人设", False),
    ("!doing", "多端", "当前活动", False), ("!presence", "多端", "在线状态", False), ("!route", "多端", "消息路由", False),
    ("!gw", "多端", "网关", True), ("!config", "多端", "配置", True), ("!code", "多端", "配对码", True), ("!apikeys", "多端", "API keys", True),
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


MEMORY_ITEMS = [
    {"id": 1, "target_id": OWNER_QQ, "content": "昨天方案过了，终于松了口气。", "tags": ["工作", "情绪"], "source": "chat", "longterm": False, "created_at": "2026-11-22 21:04:00"},
    {"id": 2, "target_id": OWNER_QQ, "content": "这个月结余三千三，旅行目标到六成了。", "tags": ["存钱", "旅行"], "source": "chat", "longterm": True, "created_at": "2026-11-21 20:18:00"},
    {"id": 3, "target_id": OWNER_QQ, "content": "不喜欢香菜，喜欢窗边和热饮。", "tags": ["偏好", "生活"], "source": "chat", "longterm": True, "created_at": "2026-11-20 19:30:00"},
    {"id": 4, "target_id": "10002", "content": "最近在看的书是《十日终焉》。", "tags": ["阅读"], "source": "chat", "longterm": False, "created_at": "2026-11-19 21:04:00"},
    {"id": 5, "target_id": OWNER_QQ, "content": "周五晚上一起看新番。", "tags": ["约定", "日程"], "source": "chat", "longterm": False, "created_at": "2026-11-18 22:12:00"},
]
MEMORY_EVENTS = [
    {"id": 1, "title": "旅行目标完成 60%", "kind": "savings", "created_at": "2026-11-18 10:00:00"},
    {"id": 2, "title": "读完《十日终焉》第 3 章", "kind": "reading", "created_at": "2026-11-17 21:40:00"},
    {"id": 3, "title": "方案通过", "kind": "chat", "created_at": "2026-11-22 21:04:00"},
]
MEMORY_PROFILE = {
    "summary": "偏好安静、窗边、热饮；在意工作反馈和旅行目标；晚间聊天较多。",
    "keywords": ["安静", "窗边", "热饮", "旅行", "读书", "猫"],
}

WEEKLY = {
    3: [
        {"name": "大学物理实验C9903班", "teacher": "5106.罗水平", "location": "未定", "weekday": 1, "weekday_name": "星期一", "period_start": 1, "period_end": 2, "weeks_raw": "3-5,7(未定)", "weeks": [3, 4, 5, 7], "start_week": 3, "end_week": 7, "source": "jwc_html"},
        {"name": "大学英语Ⅲ0203班", "teacher": "4930.徐小芳", "location": "5-628（南楼）", "weekday": 1, "weekday_name": "星期一", "period_start": 3, "period_end": 4, "weeks_raw": "3-17(5-628（南楼）)", "weeks": list(range(3, 18)), "start_week": 3, "end_week": 17, "source": "jwc_html"},
    ]
}




def _make_sticker_png(bg, accent):
    size = 96
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            dx, dy = x - 48, y - 48
            inside = dx * dx + dy * dy <= 43 * 43
            if not inside:
                row += bytes((0, 0, 0, 0))
                continue
            c = bg
            if (x - 33) ** 2 + (y - 38) ** 2 <= 28 or (x - 63) ** 2 + (y - 38) ** 2 <= 28:
                c = (255, 255, 255)
            if (x - 35) ** 2 + (y - 40) ** 2 <= 12 or (x - 61) ** 2 + (y - 40) ** 2 <= 12:
                c = (40, 45, 60)
            if 28 <= x <= 68 and 58 <= y <= 62:
                c = accent
            row += bytes((c[0], c[1], c[2], 255))
        rows.append(bytes(row))
    raw = b"".join(rows)
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")

STICKER_SPECS = [
    ("happy", "开心", (255, 214, 102), (240, 118, 94)),
    ("calm", "安静", (167, 216, 255), (82, 130, 210)),
    ("sleepy", "困困", (196, 181, 253), (120, 100, 190)),
    ("love", "喜欢", (255, 182, 193), (220, 80, 120)),
    ("shy", "害羞", (255, 204, 188), (230, 120, 100)),
    ("cheer", "加油", (167, 243, 208), (40, 150, 110)),
]
STICKERS = [{"id": sid, "name": name, "url": _make_sticker_png(bg, accent), "mime": "image/png"} for sid, name, bg, accent in STICKER_SPECS]

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
        if not auth.startswith("Bearer "):
            return False
        return auth[len("Bearer "):] in AUTH_TOKENS

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
        if path == "/api/avatar":
            kind = (q.get("type") or ["qq"])[0]
            ident = (q.get("id") or [""])[0]
            if not ident:
                self._json(400, {"error": "missing id"})
                return
            url = ("https://p.qlogo.cn/gh/" + ident + "/" + ident + "/100") if kind == "group" else ("https://q1.qlogo.cn/g?b=qq&nk=" + ident + "&s=100")
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            return
        if path == "/api/app/update":
            self._json(200, {
                "versionCode": 35820,
                "versionName": "35.8.2",
                "apkUrl": "",
                "notes": "mock 更新通道：当前已是最新开发版",
                "mock": True,
            })
            return
        if not self._authorized():
            self._json(401, {"error": "unauthorized", "message": "bad token"})
            return

        if path == "/api/stickers":
            self._json(200, {"ok": True, "data": [{"id": x["id"], "name": x["name"], "url": x["url"], "mime": x["mime"]} for x in STICKERS], "mock": True})
            return
        if path == "/api/push/devices":
            self._json(200, {"ok": True, "data": list(PUSH_DEVICES.values()), "preferences": PUSH_PREFS, "mock": True})
            return
        if path == "/api/push/outbox":
            self._json(200, {"ok": True, "data": list(PUSH_OUTBOX.values()), "mock": True})
            return
        if path == "/api/status":
            self._json(200, {
                "status": "running",
                "version": VERSION,
                "schema": "36",
                "self_qq": "",
                "mock": True,
                "master_qq": OWNER_QQ,
                "deepseek": True,
                "doubao": False,
                "clip": False,
                "sticker_api": True,
                "stats": {"images": 12, "memories": 4, "events": 7, "logs": len(LOGS), "keywords": 9, "ai_responses": 21},
                "runtime": {"dialogue_targets": len(MEMORY), "global_keywords": 9, "stickers": len(STICKERS), "daily_triggers": 2},
            })
            return
        if path == "/api/conversations":
            rows = []
            for tid in MEMORY.keys():
                items = _history(tid)
                last = items[-1] if items else {}
                rows.append({
                    "target_id": tid,
                    "name": ("测试私聊" if tid == OWNER_QQ else GROUP_META.get(tid, {}).get("name", "测试群 " + tid)),
                    "type": "private" if tid == OWNER_QQ else "group",
                    "member_count": 0 if tid == OWNER_QQ else GROUP_META.get(tid, {}).get("member_count", 5),
                    "count": len(items),
                    "last_message": str(last.get("content") or "")[:40],
                    "updated_at": str(last.get("created_at") or ""),
                    "last_read_id": int(READS.get(tid, 0)),
                    "unread": len([x for x in items if int(x.get("id") or 0) > int(READS.get(tid, 0))]),
                })
            rows.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
            self._json(200, {"ok": True, "data": rows, "mock": True})
            return
        if path == "/api/read-state":
            target = (q.get("target_id") or [OWNER_QQ])[0]
            last = int(READS.get(target, 0))
            self._json(200, {"ok": True, "target_id": target, "last_read_id": last, "unread": len([x for x in _history(target) if int(x.get("id") or 0) > last]), "mock": True})
            return
        if path == "/api/history":
            target = (q.get("target_id") or [OWNER_QQ])[0]
            limit = max(1, min(int((q.get("limit") or ["100"])[0]), 100))
            after_raw = (q.get("after_seq") or [""])[0]
            if after_raw != "":
                try:
                    after_seq = int(after_raw)
                except ValueError:
                    self._json(400, {"error": "bad_after_seq"})
                    return
                rows = [x for x in _history(target) if int(x.get("id") or 0) > after_seq]
                rows = rows[:limit]
            else:
                rows = _history(target)[-limit:]
            seqs = [int(x.get("id") or 0) for x in rows]
            self._json(200, {"ok": True, "target_id": target, "data": rows, "next_seq": max(seqs) if seqs else int(after_raw or 0), "has_more": len(rows) >= limit, "mock": True})
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
            data = [{"name": name, "group": group, "help": help_text, "owner": owner} for name, group, help_text, owner in COMMAND_CATALOG]
            self._json(200, {"ok": True, "count": len(data), "data": data, "mock": True})
            return
        if path == "/api/memory/items":
            q = (parse_qs(urlparse(self.path).query).get("q") or [""])[0].strip().lower()
            tag = (parse_qs(urlparse(self.path).query).get("tag") or [""])[0].strip()
            source = (parse_qs(urlparse(self.path).query).get("source") or [""])[0].strip()
            rows = [x for x in MEMORY_ITEMS if (not q or q in x["content"].lower()) and (not tag or tag in x["tags"]) and (not source or x["source"] == source)]
            self._json(200, {"ok": True, "count": len(rows), "data": rows, "mock": True})
            return
        if path == "/api/memory/events":
            self._json(200, {"ok": True, "count": len(MEMORY_EVENTS), "data": MEMORY_EVENTS, "mock": True})
            return
        if path == "/api/memory/stats":
            self._json(200, {"ok": True, "total": len(MEMORY_ITEMS), "targets": len({x["target_id"] for x in MEMORY_ITEMS}), "longterm": len([x for x in MEMORY_ITEMS if x["longterm"]]), "mock": True})
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

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not self._authorized():
            self._json(401, {"error": "unauthorized", "message": "bad token"})
            return
        if path.startswith("/api/push/devices/"):
            did = path.rsplit("/", 1)[-1]
            device = PUSH_DEVICES.pop(did, None)
            if not device:
                self._json(404, {"error": "device_not_found"})
                return
            self._json(200, {"ok": True, "deleted": did, "mock": True})
            return
        self._json(404, {"error": "not_found", "path": path})

    def do_PATCH(self):
        path = urlparse(self.path).path
        if path != "/api/push/preferences":
            self._json(404, {"error": "not_found", "path": path})
            return
        if not self._authorized():
            self._json(401, {"error": "unauthorized", "message": "bad token"})
            return
        body = self._body()
        if "messages" in body: PUSH_PREFS["messages"] = bool(body["messages"])
        if "reminders" in body: PUSH_PREFS["reminders"] = bool(body["reminders"])
        if "dnd" in body: PUSH_PREFS["dnd"] = bool(body["dnd"])
        self._json(200, {"ok": True, "preferences": PUSH_PREFS, "mock": True})

    def _internal_get(self, path, q):
        if path == "/internal/history":
            target = (q.get("target_id") or [OWNER_QQ])[0]
            limit = int((q.get("limit") or ["30"])[0])
            rows = _history(target)[-max(1, min(limit, 100)):]
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
        if path == "/api/groups":
            name = str(body.get("name") or "").strip()
            members = body.get("members") or []
            if len(name) < 1 or len(name) > 40:
                self._json(400, {"ok": False, "error": "bad_name", "message": "群名长度不正确"})
                return
            gid = "h_" + uuid.uuid4().hex[:12]
            CUSTOM_GROUPS[gid] = []
            MEMORY[gid] = []
            GROUP_META[gid] = {"name": name, "member_count": len(members) if isinstance(members, list) else 0, "members": members}
            self._json(200, {"ok": True, "id": gid, "name": name, "type": "group", "members": members, "mock": True})
            return
        if path == "/api/auth/login":
            qq = str(body.get("qq") or "").strip()
            password = str(body.get("password") or "")
            user = AUTH_USERS.get(qq)
            if not user or user.get("password") != password:
                self._json(401, {"ok": False, "error": "bad_credentials", "message": "QQ 或密码不正确"})
                return
            self._json(200, {"ok": True, "qq": qq, "token": user.get("token"), "mock": True})
            return
        if path == "/api/auth/setup":
            qq = str(body.get("qq") or "").strip()
            password = str(body.get("password") or "")
            code = str(body.get("setup_code") or "").strip()
            if qq not in AUTH_USERS and (not qq.isdigit() or len(qq) < 5):
                self._json(400, {"ok": False, "error": "bad_qq", "message": "QQ 格式不正确"})
                return
            if len(password) < 6:
                self._json(400, {"ok": False, "error": "weak_password", "message": "密码至少 6 位"})
                return
            if qq in AUTH_USERS:
                self._json(409, {"ok": False, "error": "user_exists", "message": "该账号已设置过密码"})
                return
            if code not in SETUP_CODES or SETUP_CODES[code]:
                self._json(403, {"ok": False, "error": "bad_setup_code", "message": "setup code 无效或已使用"})
                return
            SETUP_CODES[code] = True
            token = "h_" + uuid.uuid4().hex
            AUTH_USERS[qq] = {"password": password, "token": token}
            AUTH_TOKENS.add(token)
            self._json(200, {"ok": True, "qq": qq, "token": token, "mock": True})
            return
        if not self._authorized():
            self._json(401, {"error": "unauthorized", "message": "bad token"})
            return
        if path == "/api/push/devices":
            platform = str(body.get("platform") or "android").strip()
            topic = str(body.get("topic") or "").strip()
            endpoint = str(body.get("endpoint") or "").strip()
            if not topic:
                self._json(400, {"error": "missing_topic"})
                return
            existing = next((d for d in PUSH_DEVICES.values() if d.get("topic") == topic), None)
            if existing:
                existing["last_seen_at"] = _now()
                existing["platform"] = platform
                existing["endpoint"] = endpoint
                if existing["id"] not in PUSH_TIMERS:
                    _schedule_test_push(existing)
                self._json(200, {"ok": True, "data": existing, "created": False, "mock": True})
                return
            did = uuid.uuid4().hex[:12]
            device = {
                "id": did,
                "user_id": OWNER_QQ,
                "platform": platform,
                "topic": topic,
                "endpoint": endpoint,
                "created_at": _now(),
                "last_seen_at": _now(),
                "revoked_at": None,
            }
            PUSH_DEVICES[did] = device
            _schedule_test_push(device)
            self._json(201, {"ok": True, "data": device, "created": True, "mock": True})
            return
        if path == "/api/app/update":
            self._json(200, {
                "versionCode": 35820,
                "versionName": "35.8.2",
                "apkUrl": "",
                "notes": "mock 更新通道：当前已是最新开发版",
                "mock": True,
            })
            return
        if not self._authorized():
            self._json(401, {"error": "unauthorized", "message": "bad token"})
            return

        if path in ("/api/push/test", "/api/push/outbox"):
            if not PUSH_PREFS.get("messages", True) or PUSH_PREFS.get("dnd"):
                self._json(200, {"ok": True, "queued": 0, "reason": "preferences_off", "mock": True})
                return
            title = str(body.get("title") or "Hoshinoumi")
            text = str(body.get("body") or "新消息")
            deep_link = str(body.get("deep_link") or "/chat")
            dedupe = str(body.get("dedupe_key") or "")
            now = _now()
            queued = 0
            for device in PUSH_DEVICES.values():
                if device.get("revoked_at"):
                    continue
                key = f"{device['id']}:{dedupe}" if dedupe else ""
                if key and any(x.get("dedupe_key") == key and x.get("status") in ("pending", "sent") for x in PUSH_OUTBOX.values()):
                    continue
                oid = uuid.uuid4().hex[:12]
                PUSH_OUTBOX[oid] = {
                    "id": oid,
                    "user_id": OWNER_QQ,
                    "device_id": device["id"],
                    "kind": "message",
                    "title": title,
                    "body": text,
                    "deep_link": deep_link,
                    "dedupe_key": key,
                    "status": "pending",
                    "attempts": 0,
                    "next_at": now,
                    "created_at": now,
                }
                queued += 1
            self._json(200, {"ok": True, "queued": queued, "data": list(PUSH_OUTBOX.values()), "mock": True})
            return
        if path.startswith("/api/push/outbox/") and path.endswith("/retry"):
            oid = path.split("/")[-2]
            job = PUSH_OUTBOX.get(oid)
            if not job:
                self._json(404, {"error": "outbox_not_found"})
                return
            if job["attempts"] >= 3:
                job["status"] = "failed"
                self._json(409, {"error": "attempts_exhausted", "data": job, "mock": True})
                return
            job["attempts"] += 1
            job["status"] = "pending" if job["attempts"] < 3 else "failed"
            job["next_at"] = (datetime.now() + timedelta(minutes=job["attempts"])).strftime("%Y-%m-%d %H:%M:%S")
            self._json(200, {"ok": True, "data": job, "mock": True})
            return
        if path.startswith("/api/messages/") and path.endswith("/recall"):
            try:
                mid = int(path.split("/")[-2])
            except (TypeError, ValueError):
                self._json(400, {"error": "bad_message_id"})
                return
            item = next((x for x in _all_history() if int(x.get("id") or 0) == mid), None)
            if not item:
                self._json(404, {"error": "message_not_found"})
                return
            item["recalled"] = True
            item["content"] = ""
            item.pop("image_url", None)
            item.pop("audio_url", None)
            self._json(200, {"ok": True, "message_id": mid, "recalled": True, "mock": True})
            return
        if path == "/api/topic":
            target = str(body.get("target_id") or OWNER_QQ)
            last = ""
            for x in reversed(_history(target)):
                if x.get("role") == "user":
                    last = str(x.get("content") or "")
                    break
            closed = any(last.endswith(x) for x in ("晚安", "拜拜", "先这样", "去忙了", "睡了", "嗯"))
            self._json(200, {"ok": True, "target_id": target, "status": "closed" if closed else "open", "reason": "mock", "followup": "要接着聊吗？", "mock": True})
            return
        if path == "/api/read":
            target = str(body.get("target_id") or OWNER_QQ)
            last = int(body.get("last_read_id") or 0)
            READS[target] = max(int(READS.get(target, 0)), last)
            self._json(200, {"ok": True, "target_id": target, "last_read_id": READS[target], "unread": len([x for x in _history(target) if int(x.get("id") or 0) > READS[target]]), "mock": True})
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
            sticker = str(body.get("sticker", "")).strip()
            audio = str(body.get("audio", "")).strip()
            if not message and not image and not sticker and not audio:
                self._json(400, {"error": "empty_message", "message": "message/attachment is empty"})
                return
            if audio:
                reply = "收到一段语音（mock）。"
                _history(target).append({"id": len(_history(target)) + 1, "role": "user", "content": message or "[语音]", "audio_url": audio, "kind": "voice", "created_at": _now()})
                _history(target).append({"id": len(_history(target)) + 1, "role": "assistant", "content": reply, "created_at": _now()})
                _publish_chat(target, reply)
                self._json(200, {"reply": reply, "target_id": target, "mock": True, "time": _now()})
                return
            if sticker:
                reply = "收到一个表情包（mock）。"
                _history(target).append({"id": len(_history(target)) + 1, "role": "user", "content": message or "[表情包]", "image_url": sticker, "kind": "sticker", "created_at": _now()})
                _history(target).append({"id": len(_history(target)) + 1, "role": "assistant", "content": reply, "created_at": _now()})
                _publish_chat(target, reply)
                self._json(200, {"reply": reply, "target_id": target, "mock": True, "time": _now()})
                return
            if image:
                reply = "收到一张图片（mock）。"
                _history(target).append({"id": len(_history(target)) + 1, "role": "user", "content": message or "[图片]", "image_url": image, "kind": "image", "created_at": _now()})
                _history(target).append({"id": len(_history(target)) + 1, "role": "assistant", "content": reply, "created_at": _now()})
                _publish_chat(target, reply)
                self._json(200, {"reply": reply, "target_id": target, "mock": True, "time": _now()})
                return
            reply = {
                "你好": "你好呀。",
                "在吗": "在的，你说。",
                "存钱": "本月结余 ¥3,300，旅行目标 60%。",
                "书": "我在看《十日终焉》，窗边光线刚好。",
            }.get(message, f"收到：{message}（mock 网关）")
            _history(target).append({"id": len(_history(target)) + 1, "role": "user", "content": message, "created_at": _now()})
            _history(target).append({"id": len(_history(target)) + 1, "role": "assistant", "content": reply, "created_at": _now()})
            _publish_chat(target, reply)
            self._json(200, {"reply": reply, "target_id": target, "mock": True, "time": _now()})
            return
        if path.startswith("/api/tools/") and path.endswith("/call"):
            arg = str(body.get("arg") or "").strip()
            self._json(200, {"ok": True, "tool": "search_images", "result": f"mock 搜图：{arg or '无关键词'}（3 张）", "mock": True})
            return
        if path == "/api/command":
            cmd = str(body.get("command", "")).strip().lower()
            if cmd == "status":
                result = f"运行中（mock）\n主人 QQ：{OWNER_QQ}\n记忆：4 条\nschema：{SCHEMA}"
            elif cmd == "help":
                result = "mock 命令目录：status / help / memory / logs"
            elif cmd == "memory":
                result = "10001：3 条记忆"
            elif any(name.lstrip("!").lower() == cmd for name, _, _, _ in COMMAND_CATALOG):
                result = f"命令 !{cmd} 执行成功（mock）\n参数可用，结果仅用于界面验收。"
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
