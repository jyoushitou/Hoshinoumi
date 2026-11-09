# ===================== 运维命令（v15） =====================
# !stats  今日统计
# !config 查看/修改运行时参数

from .registry import command


@command("stats")
async def cmd_stats(ctx):
    """!stats - 今日统计（回复/配图/语音/群聊接话率）"""
    from ..core import metrics
    return metrics.describe()


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
