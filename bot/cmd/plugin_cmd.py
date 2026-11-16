# ===================== !plugin（v28.5） =====================

from .registry import command
from ..plugins.loader import install_package
from ..plugins.permissions import PermissionStore
from ..plugins.store import PluginStore


@command("plugin", "插件安装/审批/权限/列表/错误")
async def cmd_plugin(ctx):
    args = list(ctx.args or [])
    if not args:
        return ("插件命令：\n"
                "!plugin list\n!plugin install <目录>\n"
                "!plugin pending\n!plugin approve <id>\n!plugin reject <id>\n"
                "!plugin enable|disable <name>\n"
                "!plugin permission <name> <权限> <0|1|2> [scope]\n"
                "!plugin errors [name]")
    sub = args[0].lower()
    store = PluginStore()
    try:
        if sub == "list":
            rows = store.list()
            if not rows:
                return "插件：无"
            lines = ["插件："]
            for r in rows:
                flag = "✅" if r.enabled else "⏸️"
                auto = " 自启" if r.auto_start else ""
                lines.append(f"{flag} {r.name} {r.version} · {r.layer}{auto}")
            return "\n".join(lines)

        if sub == "install":
            if len(args) < 2:
                return "用法：!plugin install <目录>"
            rec = install_package(args[1], store=store)
            if rec.enabled:
                return f"插件 {rec.name} 已安装"
            aid = store.add_approval(rec.name, "install")
            return (f"插件 {rec.name} 已安装，等待审批。\n"
                    f"!plugin approve {aid}")

        if sub == "pending":
            rows = store.pending_approvals()
            if not rows:
                return "没有待审批插件"
            return "\n".join(
                f"#{r['id']} {r['plugin_name']} {r['action']} {r['created_at']}"
                for r in rows)

        if sub in ("approve", "reject"):
            if len(args) < 2:
                return f"用法：!plugin {sub} <id>"
            aid = int(args[1])
            pending = {int(r["id"]): r for r in store.pending_approvals()}
            row = pending.get(aid)
            if not row:
                return f"没有待审批 #{aid}"
            ok = store.decide(aid, "approved" if sub == "approve" else "rejected")
            if not ok:
                return "审批失败"
            if sub == "approve":
                store.set_enabled(row["plugin_name"], True)
                return f"已批准 {row['plugin_name']}，已启用"
            store.set_enabled(row["plugin_name"], False)
            return f"已拒绝 {row['plugin_name']}，保持停用"

        if sub in ("enable", "disable"):
            if len(args) < 2:
                return f"用法：!plugin {sub} <name>"
            store.set_enabled(args[1], sub == "enable")
            return f"{args[1]} 已{'启用' if sub == 'enable' else '停用'}"

        if sub == "permission":
            if len(args) < 4:
                return "用法：!plugin permission <name> <权限> <0|1|2> [scope]"
            name, permission, level = args[1], args[2], int(args[3])
            scope = " ".join(args[4:]) if len(args) > 4 else ""
            PermissionStore(name).set(permission, scope, level)
            return f"{name} {permission} {scope or '*'} = {level}"

        if sub == "errors":
            name = args[1] if len(args) > 1 else None
            rows = store.errors(name)
            if not rows:
                return "插件错误：无"
            return "\n".join(
                f"{r['plugin_name']} {r['error_type']} {r['created_at']}\n  {r['message']}"
                for r in rows)
    except Exception as e:
        return f"❌ plugin {sub} 失败：{e}"
    return f"未知 plugin 子命令：{sub}"
