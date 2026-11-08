# ===================== 时间线注入（v8-B16） =====================
# 「最近这几天发生了什么」按时间排一遍，代替「最近在忙什么」的模糊概括。

from .inject import BUDGET, trim


def _md(d):
    """把 date/datetime/字符串统一成 MM-DD"""
    if d is None:
        return "??-??"
    s = d.isoformat() if hasattr(d, "isoformat") else str(d)
    return s[5:10] if len(s) >= 10 else s


def format_timeline(rows, limit=None):
    """rows: [{"day": date, "summary": str}, ...]（已按时间倒序）

    输出：
        11-07 答辩
        11-06 加班到十点
    """
    lines = []
    for r in rows or []:
        summary = (r.get("summary") or "").strip()
        if not summary:
            continue
        lines.append(f"{_md(r.get('day'))} {summary}")
    text = "\n".join(lines) if lines else "无"
    return trim(text, limit or BUDGET["timeline"])


def build_timeline_text(tid, days=7, limit=12):
    """给 prompt 用：最近 N 天的时间线；读库失败返回「无」"""
    try:
        from ..infra.repo_memory import load_timeline
        return format_timeline(load_timeline(tid, days=days, limit=limit))
    except Exception:
        return "无"
