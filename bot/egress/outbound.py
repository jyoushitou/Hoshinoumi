# ===================== 唯一出站口（v17.2.0） =====================
# 所有 WebSocket 发送都从这里过，别的模块不许直接 `ws.send`。
#
# 为什么需要：
#   - 并发发送时 JSON 帧可能交错（心跳插进气泡中间、两张图串成一帧）
#   - 断线补发、echo 等待、入队逻辑散落在多个函数里，容易漏
#   - 出问题时要能一眼看到「谁发了什么、发了几条、失败几条」
#
# 四条保证：
#   1. 全局锁：同一时刻只有一个 `ws.send` 在跑
#   2. 断线入队：连接不可用时不丢消息，重连后补发
#   3. echo 等待：需要 message_id 的操作（撤回/取消息）走同一条路
#   4. 计数：按 kind 记成功/失败/入队/echo 超时

import asyncio
import json
import uuid

from ..core import state as cfg
from ..log import log_api, log_err, log_system

DEFAULT_TIMEOUT = 8.0


class Outbound:
    """WebSocket 唯一出口"""

    def __init__(self, ws=None, lock=None):
        self._ws = ws
        self._lock = lock if lock is not None else cfg.send_lock
        self._sent = 0
        self._failed = 0
        self._queued = 0
        self._echo_timeout = 0
        self._by_kind = {}

    # ---------- 连接 ----------

    def bind(self, ws):
        """重连/首次连接时绑定（或换掉）当前 socket"""
        self._ws = ws

    @property
    def ws(self):
        return self._ws

    def alive(self):
        return bool(self._ws) and not getattr(self._ws, "closed", False)

    # ---------- 发送 ----------

    async def send(self, action, params, label="", kind="chat",
                   want_response=False, timeout=DEFAULT_TIMEOUT):
        """发一条报文

        返回：
          - 不需要回包：True 成功 / False 失败（已入队）
          - 需要回包：NapCat 的 data dict / None 失败或超时
        """
        label = label or action
        echo = None
        fut = None

        if want_response:
            echo = uuid.uuid4().hex
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            cfg.pending_echo[echo] = fut
            payload = json.dumps({"action": action, "params": params, "echo": echo},
                                 ensure_ascii=False)
        else:
            payload = json.dumps({"action": action, "params": params},
                                 ensure_ascii=False)

        if not self.alive():
            self._enqueue(payload, label, kind)
            if fut is not None:
                cfg.pending_echo.pop(echo, None)
            return None if want_response else False

        try:
            async with self._lock:                 # ★ 全局锁：一次只发一帧
                await self._ws.send(payload)
            self._count(kind, "sent")
            self._sent += 1
            log_api(f"[出站] {label} 已发送（{len(payload)} 字节）")
        except Exception as e:
            self._count(kind, "failed")
            self._failed += 1
            log_err(f"[出站] {label} 发送失败: {e}")
            self._enqueue(payload, label, kind)
            if fut is not None:
                cfg.pending_echo.pop(echo, None)
            return None if want_response else False

        if fut is None:
            return True

        try:
            return await asyncio.wait_for(fut, timeout)
        except Exception:
            self._echo_timeout += 1
            self._count(kind, "echo_timeout")
            log_err(f"[出站] {label} 等回包超时（{timeout}s）")
            return None
        finally:
            cfg.pending_echo.pop(echo, None)

    # ---------- 补发 ----------

    async def flush(self):
        """重连后补发积压消息，返回补发条数"""
        if not self.alive() or not cfg.pending_outbox:
            return 0
        sent = 0
        while cfg.pending_outbox:
            payload = cfg.pending_outbox[0]
            try:
                async with self._lock:
                    await self._ws.send(payload)
                cfg.pending_outbox.popleft()
                sent += 1
            except Exception as e:
                log_err(f"[出站] 补发失败，保留队列: {e}")
                break
        if sent:
            self._sent += sent
            log_system(f"[出站] 断线消息补发完成: {sent} 条")
        return sent

    # ---------- 内部 ----------

    def _enqueue(self, payload, label, kind):
        cfg.pending_outbox.append(payload)
        self._queued += 1
        self._count(kind, "queued")
        log_err(f"[出站] {label}: 连接不可用，已入队"
                f"（队列 {len(cfg.pending_outbox)} 条）")

    def _count(self, kind, field):
        item = self._by_kind.setdefault(kind, {"sent": 0, "failed": 0,
                                               "queued": 0, "echo_timeout": 0})
        item[field] = item.get(field, 0) + 1

    # ---------- 观测 ----------

    def stats(self):
        return {
            "alive": self.alive(),
            "sent": self._sent,
            "failed": self._failed,
            "queued": self._queued,
            "echo_timeout": self._echo_timeout,
            "pending": len(cfg.pending_outbox),
            "by_kind": {k: dict(v) for k, v in self._by_kind.items()},
        }

    def describe(self):
        s = self.stats()
        state = "在线" if s["alive"] else "离线"
        text = (f"📤 出站：{state} | 已发 {s['sent']} | 失败 {s['failed']} | "
                f"入队 {s['queued']}（积压 {s['pending']}）")
        if s["echo_timeout"]:
            text += f" | 回包超时 {s['echo_timeout']}"
        return text


_out = None


def get_outbound():
    """全局出站口（懒加载）"""
    global _out
    if _out is None:
        _out = Outbound()
    return _out


def set_outbound(obj):
    """测试用"""
    global _out
    _out = obj
