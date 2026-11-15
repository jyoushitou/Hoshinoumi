import asyncio

# ===================== 主程序入口 =====================
# v5-R5：初始化在 app/bootstrap.py，主循环在 app/loop.py，这里只做装配

from .log import log_system, log_err
from .server import start_api_server
from .app.bootstrap import bootstrap
from .app.loop import serve
from .core import hot_reload


async def main():
    """启动机器人：初始化 → 起 API 服务器 → 常驻服务循环"""
    bootstrap()

    # ===================== 启动 API 服务器 =====================
    try:
        api_runner = await start_api_server()  # 启动 HTTP API 服务器
        log_system("API 服务器已启动")
    except Exception as e:
        log_err(f"API 服务器启动失败: {e}")
        api_runner = None  # API 服务器启动失败不影响主流程

    # ===================== 主循环 =====================
    watcher = asyncio.create_task(hot_reload.watch())  # v25.1
    try:
        await serve(api_runner)
    finally:
        watcher.cancel()
        try:
            await watcher
        except Exception:
            pass

