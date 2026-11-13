# ===================== 兼容层（弃用别名） =====================
# v5-R6 起数据访问已迁到 bot/infra/*；v17.14 起本文件是**弃用别名**：
# 只 re-export + 打一次警告，v18 删除。
#
# 新代码请直接：
#     from ..infra.conn import get_cursor
#     from ..infra.repo_log import write_log_to_db
#     from ..infra.repo_memory import ...

from .infra.conn import get_db, get_cursor  # noqa: F401
from .infra.repo_log import write_log_to_db  # noqa: F401
from .infra.repo_key import get_api_key_from_db, reload_api_keys  # noqa: F401
from .infra.repo_memory import (  # noqa: F401
    load_user_memories_from_db,
    add_user_memory_to_db,
    load_global_keywords_from_db,
    add_global_keywords_to_db,
    load_events_from_db,
    add_event_to_db,
)
from .infra.repo_ai import save_ai_raw_response, get_recent_usage  # noqa: F401

_WARNED = False


def _warn_once():
    """第一次被导入时提醒一次（不刷屏）"""
    global _WARNED
    if _WARNED:
        return
    _WARNED = True
    try:
        import sys

        print("[弃用] bot.db 将在 v18 删除，请改用 bot.infra.repo_*",
              file=sys.stderr)
    except Exception:
        pass


_warn_once()
