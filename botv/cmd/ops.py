# ===================== 运维命令（v15） =====================
# !stats  今日统计
# !config 查看/修改运行时参数

from .registry import command


@command("stats")
async def cmd_stats(ctx):
    """!stats - 今日统计（回复/配图/语音/群聊接话率）"""
    from ..core import metrics

    lines = [metrics.describe()]
    try:
        from ..infra.blocking import describe_threads
        lines.append(describe_threads())
    except Exception:
        pass
    try:
        from ..infra.pool import describe_conns
        lines.append(describe_conns())
    except Exception:
        pass
    try:
        from ..scheduler.dispatcher import get_scheduler
        lines.append(get_scheduler().describe())   # 未启动时也会显示队列长度
    except Exception:
        pass
    try:
        from ..infra.cache import describe as describe_cache
        lines.append(describe_cache())
    except Exception:
        pass
    try:
        from ..infra.repo_memory import dual_write_stats
        dw = dual_write_stats()
        if dw.get("fail"):
            lines.append(f"⚠️ 双写失败：{dw['fail']} 次")
    except Exception:
        pass
    try:
        from ..schedule import cron
        lines.append("⏰ 定时：" + cron.next_summary())
    except Exception:
        pass
    try:
        from ..egress.outbound import get_outbound
        lines.append(get_outbound().describe())
    except Exception:
        pass
    try:
        from ..cmd.channel import get_channel
        lines.append(get_channel().describe())
    except Exception:
        pass
    try:
        from ..infra.txtlog import describe as describe_log
        lines.append(describe_log())
    except Exception:
        pass
    try:
        from ..infra.monitor import describe as describe_monitor
        lines.append(describe_monitor())
    except Exception:
        pass
    return "\n".join(lines)


@command("version")
async def cmd_version(ctx):
    """!version - 当前版本、提交、运行时长"""
    from ..core import version as V

    return V.describe()


@command("vision")
async def cmd_vision(ctx):
    """!vision test - 视觉自检（画一张测试图跑一遍）"""
    from ..ai.vision import self_test

    return await self_test()


@command("config")
async def cmd_config(ctx):
    """!config - 查看可调参数；!config <参数> <值> 修改"""
    from ..core import tunables

    args = ctx.args
    if not args:
        lines = ["⚙️ 可调参数（改完立即生效，重启也记得）："]
        for name, value, desc in tunables.all_items():
            lines.append(f"  {name} = {value}   —— {desc}")
        lines.append("用法：!config <参数> <值>")
        return "\n".join(lines)

    if len(args) < 2:
        return "用法：!config <参数> <值>\n例如：!config image_prob 0.2"

    ok, msg = tunables.set_value(args[0], args[1])
    return ("✅ " if ok else "❌ ") + msg
