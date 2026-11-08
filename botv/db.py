# ===================== 兼容层 =====================
# v5-R6：数据访问已迁至 botv/infra/*
# 本文件只做转发；所有调用方迁完后可删除

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
