# ===================== 管理类命令 =====================
# reload / set / code / exit：会改变运行时状态
# 迁移自 commands.py（v5-R5）

import asyncio
import os
import threading
import time as _time

from bot.core import state as cfg
from ..config import MASTER_QQ, HEARTBEAT_INTERVAL
from ..infra.repo_key import reload_api_keys
from ..log import log_system
from ..memory import load_memories
from ..send import send_private_msg, send_group_msg
from .registry import command, COMMANDS, Command


@command("reload")
async def cmd_reload(ctx):
    """!reload - 重新加载密钥与记忆"""
    try:
        reload_api_keys()
        load_memories()
        return "♻️ 已重新加载API密钥和记忆数据"
    except Exception as e:
        return f"❌ 重载失败: {e}"


@command("set")
async def cmd_set(ctx):
    """!set <键> <值> - 修改运行时配置"""
    parts = ctx.parts
    if len(parts) < 3:
        return "用法: !set <键> <值>\n支持: master_qq, heartbeat"
    key = parts[1].lower()
    val = " ".join(parts[2:])
    try:
        if key == "master_qq":
            new_val = int(val)
            # 保持旧行为：改的是 commands 模块内的副本（历史遗留，v6 再统一到 cfg）
            import bot.commands as _legacy
            _legacy.MASTER_QQ = new_val
            return f"✅ 主人QQ已设为 {new_val}"
        elif key == "heartbeat":
            new_val = int(val)
            import bot.commands as _legacy
            _legacy.HEARTBEAT_INTERVAL = new_val
            return f"✅ 心跳间隔已设为 {new_val}s"
        else:
            return f"❌ 不支持的配置项: {key}"
    except Exception as e:
        return f"❌ 设置失败: {e}"


@command("code")
async def cmd_code(ctx):
    """!code / !code off - 代码模式开关"""
    parts = ctx.parts
    is_off = len(parts) > 1 and parts[1].lower() == "off"

    if is_off:
        # 请求退出
        if not cfg.CODE_MODE:
            return "ℹ️ 当前不在代码模式，无需退出"
        cfg.CODE_MODE = False
        cfg.CODE_MODE_LAST_MSG_TIME = 0
        return "🔧 已退出代码模式，恢复人设回复"
    else:
        # 请求进入
        if cfg.CODE_MODE:
            # 已在代码模式：提示当前状态
            if cfg.CODE_MODE_LAST_MSG_TIME > 0:
                elapsed = int(_time.time() - cfg.CODE_MODE_LAST_MSG_TIME)
                time_desc = f"{elapsed}秒" if elapsed < 60 else f"{elapsed//60}分{elapsed%60}秒"
                return (
                    f"🔧 已在代码模式（距上次消息 {time_desc}）\n"
                    "知识正确性优先，输入 !code off 可手动退出"
                )
            return "🔧 已在代码模式，输入 !code off 可手动退出"
        # 正常开启
        cfg.CODE_MODE = True
        cfg.CODE_MODE_LAST_MSG_TIME = _time.time()
        return (
            "🔧 已开启代码模式！\n"
            "知识正确性优先于角色人设，30分钟无消息将自动退出。\n"
            "输入 !code off 可手动退出。"
        )


async def _do_exit(ctx):
    """执行退出流程：先回消息，再触发 shutdown_event"""
    uid, ws, is_group, gid = ctx.uid, ctx.ws, ctx.is_group, ctx.gid
    if not getattr(cfg, "shutdown_event", None) or not cfg.shutdown_event.is_set():
        msg = [{"type": "text", "data": {"text": "🛑 程序退出中..."}}]
        if is_group:
            await send_group_msg(gid, msg, ws)
        else:
            await send_private_msg(uid, msg, ws)
        log_system(f"[!exit] 收到退出命令，正在设置退出事件")
        cfg.shutdown_event.set()

        # v18.20：5 秒看门狗——serve() 干净退出失败时强制结束进程
        def _watchdog():
            log_system("[!exit] 5 秒看门狗触发，强制退出")
            os._exit(0)

        _t = threading.Timer(5.0, _watchdog)
        _t.daemon = True
        _t.start()

        await asyncio.sleep(0.8)
        log_system(f"[!exit] 退出事件已触发，程序即将退出")
        return ""
    log_system(f"[!exit] 重复收到退出命令")
    return "ℹ️ 程序已在退出中..."


@command("exit")
async def cmd_exit(ctx):
    """!exit / !quit - 安全退出"""
    return await _do_exit(ctx)


# quit 是 exit 的别名，注册同一个处理器
COMMANDS["quit"] = Command(name="quit", handler=cmd_exit, help_text="!quit - 同 !exit")
