# ===================== 主循环 =====================
# WebSocket 服务 + 心跳 + 定时任务，异常自动重启
# 迁移自 main.py（v5-R5），逻辑逐字未改

import asyncio

import websockets

from botv.core import state as cfg
from ..config import LISTEN_HOST, LISTEN_PORT_QQ
from ..log import log_system, log_err
from ..heartbeat import heartbeat_monitor
from ..schedule import cycle_task_run
from ..chat.handler import websocket_handle_qq


MAX_RESTARTS = 10          # 连续失败多少次就放弃
BACKOFF_BASE = 5           # 首次等待 5 秒
BACKOFF_MAX = 60           # 退避封顶 60 秒


async def serve(api_runner):
    """常驻服务循环：收到 shutdown_event 时安全退出

    v17.10：端口被占用这类错误不能无限重启——连续失败 10 次就退出，
    间隔按 5→10→20→40→60 秒退避，别再每 5 秒刷一条日志。
    """
    failures = 0
    while True:
        # 收到 !exit 命令后安全退出
        if getattr(cfg, "shutdown_event", None) and cfg.shutdown_event.is_set():
            log_system("收到退出命令，正在安全关闭...")
            last_ws = cfg.active_ws_qq
            if last_ws and not getattr(last_ws, "closed", False):  # 关闭 WebSocket 连接
                try:
                    await last_ws.close()
                except Exception:
                    pass
            if api_runner:  # 清理 API 服务器
                try:
                    await api_runner.cleanup()
                except Exception:
                    pass
            log_system("已安全退出")
            return

        hb = asyncio.create_task(heartbeat_monitor("QQ", cfg.active_ws_qq))  # 启动心跳监控
        cyc = asyncio.create_task(cycle_task_run())  # 启动定时任务循环
        try:
            async with websockets.serve(  # 启动 WebSocket 服务器
                websocket_handle_qq, LISTEN_HOST, LISTEN_PORT_QQ,
                ping_interval=20, ping_timeout=60,  # v8-FIX：容忍短暂卡顿，别一卡就断线
            ):
                failures = 0                       # 起来了就清零
                await cfg.shutdown_event.wait()  # 保持运行，等待 !exit 命令触发退出
        except Exception as e:
            failures += 1
            log_err(f"启动失败({failures}/{MAX_RESTARTS}): {e}")
        finally:
            hb.cancel()  # 取消心跳任务
            cyc.cancel()  # 取消定时任务
            if api_runner:  # 清理 API 服务器
                try:
                    await api_runner.cleanup()
                except Exception:
                    pass
            # 检查是否因为退出命令而结束（跳过5秒重启等待）
            if getattr(cfg, "shutdown_event", None) and cfg.shutdown_event.is_set():
                log_system("已安全退出")
                return
            if failures >= MAX_RESTARTS:
                log_err(f"[退出] 连续 {failures} 次启动失败，交给 systemd 拉起")
                return
            delay = min(BACKOFF_MAX, BACKOFF_BASE * (2 ** max(0, failures - 1)))
            log_system(f"[重启] {delay:.0f} 秒后重试（第 {failures + 1} 次）")
            await asyncio.sleep(delay)
