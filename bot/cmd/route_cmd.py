# ===================== !route（v33.6.2） =====================

from .registry import command


@command("route", "查看默认链路候选与 native 回落")
async def cmd_route(ctx):
    from ..routing.router import RouteRouter
    from ..ports.route import RouteKey

    parts = ctx.args
    layer = parts[0].lower() if parts else "model"
    if layer not in ("model", "memory", "channel", "tool", "storage", "scheduler", "outbound"):
        return f"❌ 未知层：{layer}\n可用：model/memory/channel/tool/storage/scheduler/outbound"
    return RouteRouter().explain(RouteKey(layer))
