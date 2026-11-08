# ===================== WebSocket 心跳监测模块 =====================
# 定期发送 ping 帧检测连接是否存活
# v5-F6：连续失败时主动关闭连接，让 NapCat 立刻重连（看门狗）

import asyncio  # 异步 IO：定时器
from .config import HEARTBEAT_INTERVAL  # 心跳间隔（秒）
from .log import log_system  # 系统日志

# 连续多少次 ping 失败就判定连接已死
MAX_HEARTBEAT_FAILURES = 2


async def heartbeat_monitor(label: str, ws_ref):
    """通用心跳监测协程

    参数：
        label: 连接标识，如 'QQ'，用于日志区分
        ws_ref: 全局 WebSocket 变量引用（如 cfg.active_ws_qq），
                每次循环重新读取以获取最新连接状态

    行为：
        - 每 HEARTBEAT_INTERVAL 秒发送一次 ping
        - 连续 MAX_HEARTBEAT_FAILURES 次失败 → 主动 close()
          NapCat 会因此立刻重连，而不是傻等 TCP 超时
    """
    failures = 0
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)  # 等待指定间隔
        ws = ws_ref  # 重新读取全局变量（可能已被其他协程更新）
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
