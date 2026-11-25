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


@command("backup")
async def cmd_backup(ctx):
    """!backup [run|list] - 备份清单 / 立即备份"""
    from ..infra import backup

    args = [a.lower() for a in (ctx.args or [])]
    if args and args[0] == "run":
        try:
            from ..infra.blocking import run_blocking
            r = await run_blocking(backup.run_backup, name="backup")
        except Exception as e:
            return f"❌ 备份失败：{e}"
        if r.get("ok"):
            return (f"✅ 备份完成：{r['file']}（{r['size'] / 1024:.0f} KB，"
                    f"{r['tables']} 张表）")
        return f"❌ 备份失败：{r.get('error', '未知原因')}"
    return backup.describe()


@command("version")
async def cmd_version(ctx):
    """!version - 当前版本、提交、运行时长"""
    from ..core import version as V

    return V.describe()


@command("vision")
async def cmd_vision(ctx):
    """!vision [test] - 查看视觉配置；test 才跑自检"""
    if ctx.args and str(ctx.args[0]).lower() == "test":
        from ..ai.vision import self_test
        return await self_test()

    from ..ai.vision import providers
    provs = providers()
    usable = [p for p in provs if p.get("name") != "DeepSeek"]
    if not usable:
        return ("🖼️ 视觉未配置\n"
                "   缺少豆包/方舟 ARK_API_KEY 或 NAO_VISION_KEY。\n"
                "   当前只有 DeepSeek 文本模型，不能识图。\n"
                "   配置：.venv\\Scripts\\python.exe scripts\\configure_api.py\n"
                "   自检：!vision test")
    names = "、".join(p["name"] for p in usable)
    model = usable[0].get("model") or "（未配置）"
    return (f"🖼️ 视觉已配置（{names}）\n"
            f"   模型：{model}\n"
            f"   发图片时自动识别；`!vision test` 跑自检")


@command("update")
async def cmd_update(ctx):
    """!update - 查看最近一次热更新/拒绝结果"""
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "data" / "update_status.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return "还没有热更新记录。用 scripts/nao_update.py --latest 检查/更新。"
    if data.get("allowed"):
        return f"✅ 已允许热更新：{data.get('version')}（{data.get('reason')}）"
    return (f"⛔ 拒绝热更新：{data.get('version')}\n"
            f"原因：{data.get('reason')}\n"
            "当前版本继续运行，未切换。请安排维护窗口后手动升级。")

@command("config")
async def cmd_config(ctx):
    """!config - 查看可调参数；!config <参数> <值> 修改"""
    from ..core import tunables

    args = ctx.args
    from ..core import appconfig
    if not args:
        lines = ["⚙️ 上下文配置（优先级 default<config<env<runtime）："]
        for name, value, default, src, desc in appconfig.all_items():
            lines.append(f"  {name} = {value}  (默认 {default}, {src}) —— {desc}")
        lines.append("")
        lines.append("⚙️ 可调参数（改完立即生效，重启也记得）：")
        for name, value, desc in tunables.all_items():
            lines.append(f"  {name} = {value}   —— {desc}")
        lines.append("用法：!config <参数> <值>")
        return "\n".join(lines)

    if len(args) < 2:
        return "用法：!config <参数> <值>\n例如：!config image_prob 0.2"

    if args[0] in appconfig.SPEC:
        ok, msg = appconfig.set_runtime(args[0], args[1])
    else:
        ok, msg = tunables.set_value(args[0], args[1])
    return ("✅ " if ok else "❌ ") + msg
