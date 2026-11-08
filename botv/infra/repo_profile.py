# ===================== 对象画像（v7-B9） =====================
# 不新建表：画像就是 events 表里 kind='profile' 的若干行，
# 每条形如「昵称：小奈」，同一字段再写会覆盖旧的。

from ..config import CST  # noqa: F401
from .conn import get_cursor
from .dedupe import dedupe_key

# 允许的字段（其余字段也能存，只是这几个有固定语义）
PROFILE_FIELDS = ("昵称", "关系", "喜好", "禁忌", "生日", "印象")


def set_profile(tid, field, value):
    """写一条画像；同一字段会被覆盖（不累积）"""
    field = (field or "").strip()
    value = (value or "").strip()
    if not field or not value:
        return False
    c = get_cursor()
    # 先删同字段旧行，保证是「覆盖」而不是「追加」
    c.execute(
        "DELETE FROM events WHERE target_id=%s AND kind='profile' AND event_summary LIKE %s",
        (tid, f"{field}：%"),
    )
    text = f"{field}：{value}"
    c.execute(
        "INSERT INTO events(target_id, event_summary, tags, kind, dedupe_key, last_seen) "
        "VALUES(%s,%s,%s,'profile',%s,NOW())",
        (tid, text, field, dedupe_key(tid, "profile", text)),
    )
    c.connection.commit()
    return True


def get_profile(tid):
    """读画像，返回 {字段: 值}；读失败不影响回复"""
    try:
        c = get_cursor()
        c.execute(
            "SELECT event_summary FROM events WHERE target_id=%s AND kind='profile' ORDER BY id DESC",
            (tid,),
        )
        out = {}
        for r in c.fetchall():
            s = r["event_summary"] or ""
            if "：" in s:
                k, v = s.split("：", 1)
                out.setdefault(k, v)  # 新的在前，旧的忽略
        return out
    except Exception:
        return {}


def build_profile_text(tid):
    """给 prompt 用的一行画像；没有就返回「无」"""
    p = get_profile(tid)
    if not p:
        return "无"
    return "；".join(f"{k}={v}" for k, v in p.items())


def format_profile(tid):
    """给 !profile 命令看的多行文本"""
    p = get_profile(tid)
    if not p:
        return f"🧾 {tid} 还没有画像"
    lines = [f"🧾 {tid} 的画像："]
    for k, v in p.items():
        lines.append(f"  {k}：{v}")
    return "\n".join(lines)
