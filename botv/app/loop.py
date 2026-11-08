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


async def serve(api_runner):
    """常驻服务循环：收到 shutdown_event 时安全退出"""
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
                await cfg.shutdown_event.wait()  # 保持运行，等待 !exit 命令触发退出
        except Exception as e:
            log_err(f"重启:{e}")  # 异常时记录日志并自动重启
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
            await asyncio.sleep(5)  # 等待 5 秒后重启
