# ===================== 逐接口 /internal/* 契约（v35.9.36） =====================
# 网关只能调用这里登记的内部路径；路径反向映射到 worker 现有 public handler。
# 这样 worker 不再接受任意 /internal/* 或 /api/*。

import re

# (internal regex, allowed HTTP methods)
_CONTRACTS = [
    (r"/internal/health", {"GET"}),
    (r"/internal/status", {"GET"}),
    (r"/internal/avatar", {"GET"}),
    (r"/internal/usage", {"GET"}),
    (r"/internal/memory", {"GET"}),
    (r"/internal/memory/items/[^/]+", {"PATCH", "DELETE"}),
    (r"/internal/logs", {"GET"}),
    (r"/internal/token", {"GET"}),
    (r"/internal/conversations", {"GET"}),
    (r"/internal/read-state", {"GET"}),
    (r"/internal/commands", {"GET"}),
    (r"/internal/groups", {"GET", "POST"}),
    (r"/internal/endpoints", {"GET", "POST"}),
    (r"/internal/endpoints/[^/]+", {"DELETE"}),
    (r"/internal/endpoints/[^/]+/messages", {"GET"}),
    (r"/internal/endpoints/[^/]+/ack", {"POST"}),
    (r"/internal/tools", {"GET"}),
    (r"/internal/tools/[^/]+/call", {"POST"}),
    (r"/internal/persona", {"GET"}),
    (r"/internal/persona/export", {"GET"}),
    (r"/internal/persona/import", {"POST"}),
    (r"/internal/persona/activate", {"POST"}),
    (r"/internal/savings", {"GET"}),
    (r"/internal/savings/entries", {"POST"}),
    (r"/internal/savings/import", {"POST"}),
    (r"/internal/savings/snapshots", {"GET", "POST"}),
    (r"/internal/savings/reconcile", {"GET"}),
    (r"/internal/savings/init", {"GET", "POST"}),
    (r"/internal/savings/overview", {"GET"}),
    (r"/internal/savings/goals", {"GET"}),
    (r"/internal/savings/frozen", {"GET"}),
    (r"/internal/savings/fixed", {"GET", "POST"}),
    (r"/internal/savings/fixed/[^/]+/settle", {"POST"}),
    (r"/internal/savings/funds", {"GET"}),
    (r"/internal/savings/funds/buy", {"POST"}),
    (r"/internal/savings/funds/[^/]+/redeem", {"POST"}),
    (r"/internal/savings/monthly", {"GET"}),
    (r"/internal/finance/audit", {"GET"}),
    (r"/internal/savings/events", {"GET"}),
    (r"/internal/balance", {"GET"}),
    (r"/internal/health/init", {"GET", "POST"}),
    (r"/internal/health/summary", {"GET"}),
    (r"/internal/health/meals", {"POST"}),
    (r"/internal/health/meals/[^/]+", {"DELETE"}),
    (r"/internal/health/exercises", {"POST"}),
    (r"/internal/health/exercises/[^/]+", {"DELETE"}),
    (r"/internal/health/recognize", {"POST"}),
    (r"/internal/push/devices", {"GET", "POST"}),
    (r"/internal/push/devices/[^/]+", {"DELETE"}),
    (r"/internal/push/preferences", {"GET", "PATCH"}),
    (r"/internal/push/test", {"POST"}),
    (r"/internal/push/outbox", {"GET"}),
    (r"/internal/plugins", {"GET"}),
    (r"/internal/plugins/install", {"POST"}),
    (r"/internal/plugins/[^/]+/(toggle|approve|reject)", {"POST"}),
    (r"/internal/relation", {"GET"}),
    (r"/internal/weekly-plan/weeks", {"GET"}),
    (r"/internal/weekly-plan", {"GET", "POST"}),
    (r"/internal/weekly-plan/import", {"POST"}),
    (r"/internal/plan", {"GET", "POST"}),
    (r"/internal/plan/import", {"POST"}),
    (r"/internal/plan/export", {"GET"}),
    (r"/internal/presence", {"GET"}),
    (r"/internal/state", {"GET"}),
    (r"/internal/reminders", {"GET"}),
    (r"/internal/reminders/[^/]+/ack", {"POST"}),
    (r"/internal/cron", {"GET", "POST"}),
    (r"/internal/cron/[^/]+", {"PATCH", "DELETE"}),
    (r"/internal/cron/[^/]+/run", {"POST"}),
    (r"/internal/chat", {"POST"}),
    (r"/internal/command", {"POST"}),
    (r"/internal/history", {"GET"}),
    (r"/internal/read", {"POST"}),
    (r"/internal/messages/[^/]+/recall", {"POST"}),
    (r"/internal/recall", {"POST"}),
    (r"/internal/topic", {"POST"}),
    (r"/internal/diary", {"GET"}),
    (r"/internal/shelf", {"GET"}),
    # 网关内部管理调用，不暴露 public /api
    (r"/internal/auth/verify", {"POST"}),
    (r"/internal/auth/owner", {"GET"}),
    (r"/internal/auth/register", {"POST"}),
    (r"/internal/audit", {"POST"}),
]

_COMPILED = [(re.compile(pattern + r"\Z"), methods) for pattern, methods in _CONTRACTS]


def resolve(internal_path, http_method):
    """返回可调用 public 路径；不匹配返回 None。"""
    method = str(http_method or "").upper()
    for pattern, methods in _COMPILED:
        if method in methods and pattern.match(internal_path):
            if (internal_path.startswith("/internal/auth/") or
                    internal_path in ("/internal/audit", "/internal/recall",
                                      "/internal/diary", "/internal/shelf")):
                return internal_path
            return "/api/" + internal_path[len("/internal/"):]
    return None
