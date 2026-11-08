# ===================== 主程序入口 =====================
# v5-R5：初始化在 app/bootstrap.py，主循环在 app/loop.py，这里只做装配

from .log import log_system, log_err
from .server import start_api_server
from .app.bootstrap import bootstrap
from .app.loop import serve


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
    await serve(api_runner)
