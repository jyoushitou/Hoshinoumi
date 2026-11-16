# ===================== WebSocket 心跳监测模块 =====================
# 定期发送 ping 帧检测连接是否存活
# v5-F6：连续失败时主动关闭连接，让 NapCat 立刻重连（看门狗）

import asyncio  # 异步 IO：定时器
from .config import HEARTBEAT_INTERVAL  # 心跳间隔（秒）
from .log import log_system  # 系统日志
from .core.locks import cleanup_idle_locks  # 回收闲置的分片锁

# 连续多少次 ping 失败就判定连接已死
MAX_HEARTBEAT_FAILURES = 2


def _current_ws(ws_ref):
    """v27.6：支持传 callable 读取最新连接；兼容旧的对象入参。"""
    if callable(ws_ref):
        try:
            return ws_ref()
        except Exception:
            return None
    return ws_ref


async def heartbeat_monitor(label: str, ws_ref):
    """通用心跳监测协程

    参数：
        label: 连接标识，如 'QQ'，用于日志区分
        ws_ref: `lambda: cfg.active_ws_qq` 或 WebSocket 对象；
                每次循环重新读取，避免任务启动时拿到 None 后一直空转

    行为：
        - 每 HEARTBEAT_INTERVAL 秒发送一次 ping
        - 连续 MAX_HEARTBEAT_FAILURES 次失败 → 主动 close()
          NapCat 会因此立刻重连，而不是傻等 TCP 超时
    """
    failures = 0
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)  # 等待指定间隔
        cleanup_idle_locks()  # v6-E26：顺手回收闲置的对象锁
        ws = _current_ws(ws_ref)  # v27.6：每轮读取最新连接
        if not ws or getattr(ws, "closed", False):
            failures = 0
            continue
        try:
            await ws.ping()  # 发送 WebSocket ping 帧
            failures = 0
        except Exception:
            failures += 1
            log_system(f"{label}心跳失败({failures}/{MAX_HEARTBEAT_FAILURES})")
            if failures >= MAX_HEARTBEAT_FAILURES:
                log_system(f"{label}心跳连续失败，主动断开连接等待重连")
                try:
                    await ws.close()
                except Exception:
                    pass
                failures = 0
