# ===================== 会话已读位点（v35.5.7） =====================
# 单用户场景，用 bot_meta 的 read:<uid>:<target> 保存最后已读消息 id。
# 不新增表；多端共享同一后端位点。

from . import repo_meta

_PREFIX = "read:"


def _key(user_id, target_id):
    return f"{_PREFIX}{user_id}:{target_id}"


def last_read(user_id, target_id):
    raw = repo_meta.get_value(_key(user_id, target_id), "0")
    try:
        return max(0, int(raw or 0))
    except (TypeError, ValueError):
        return 0


def mark_read(user_id, target_id, last_read_id):
    from . import repo_conversation
    current = last_read(user_id, target_id)
    # 不允许倒退；也允许前端传 0 表示清空
    value = max(current, int(last_read_id or 0))
    ok = repo_meta.set_value(_key(user_id, target_id), value)
    return value if ok else current


def unread_count(user_id, target_id):
    from . import repo_conversation
    return repo_conversation.count_after(target_id, after_id=last_read(user_id, target_id), user_id=user_id)
