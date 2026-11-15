# ===================== 本地阅读记忆（v24.8.8） =====================
# 每段 1000 字只把“摘要”写进 memories(kind=book)，正文不入库。
# 之后的对话通过正常记忆检索就能看到读过的书。

from ..infra.repo_memory import add_event_to_db


def remember_chunk(user_id, tid, title, info, summary):
    summary = (summary or "").strip()
    if not summary:
        return None
    start = int(info.get("offset", 0)) + 1
    end = start + int(info.get("chars", 0)) - 1
    text = f"读《{title}》第 {start}-{end} 字：{summary}"[:900]
    return add_event_to_db(
        tid, text, tags=f"读书,{title}", kind="book", importance=2,
        user_id=user_id,
    )


def remember_finished(user_id, tid, title, total_chars):
    text = f"读完了《{title}》，全书约 {int(total_chars or 0)} 字。"[:900]
    return add_event_to_db(
        tid, text, tags=f"读书,{title},读完", kind="book", importance=2,
        user_id=user_id,
    )
