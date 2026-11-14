# ===================== !gw 网关观测（v22） =====================
from datetime import datetime, timedelta

from ..config import CST
from ..infra.conn import get_cursor
from .registry import command


@command("gw", "!gw - 网关最近请求 / 限流 / 客户端")
async def cmd_gw(ctx):
    try:
        c = get_cursor()
        c.execute(
            "SELECT owner,path,status,cost_ms,ip,created_at "
            "FROM gateway_log ORDER BY id DESC LIMIT 6")
        rows = list(c.fetchall() or [])
    except Exception as e:
        return f"🌐 网关审计读取失败：{e}"

    if not rows:
        return "🌐 网关暂无审计记录（检查 gateway_log / 网关是否在跑）"

    cutoff = (datetime.now(CST) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        c.execute("SELECT COUNT(*) AS n FROM gateway_log WHERE status=429 AND created_at>=%s",
                  (cutoff,))
        limited = int((c.fetchone() or {}).get("n") or 0)
        c.execute("SELECT COUNT(DISTINCT ip) AS n FROM gateway_log WHERE created_at>=%s",
                  (cutoff,))
        clients = int((c.fetchone() or {}).get("n") or 0)
    except Exception:
        limited = clients = -1

    lines = [f"🌐 网关观测｜近5分钟客户端 {clients}｜429 {limited}｜最近 {len(rows)} 条"]
    if limited == 0 and clients == 0:
        lines.append("（近5分钟无请求，以下为最近记录）")
    for r in reversed(rows):
        owner = r.get("owner") or "-"
        lines.append(
            f"  {r.get('created_at')} {r.get('status')} "
            f"{r.get('cost_ms')}ms {r.get('ip')} {owner} {r.get('path')}")
    return "\n".join(lines)
