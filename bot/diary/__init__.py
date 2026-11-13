# ===================== diary 包 =====================
# 日记系统（v5-R5）：store（存取）/ generate（生成）/ view（展示）/ cache（缓存）
# 本文件保持与旧 bot/diary.py 相同的对外接口

from .store import (  # noqa: F401
    ensure_diaries_table,
    get_diary_from_db,
    save_diary_to_db,
    get_events_by_date,
    get_dialogs_by_date,
    get_dates_with_events,
    count_diaries_of_target,
)
from .generate import (  # noqa: F401
    generate_diary,
    generate_missing_7day_diaries,
    _clean_diary_text,
)
from .view import get_raw_events_text, get_diary_overview  # noqa: F401
from .cache import CACHE_TTL, MAX_CACHE  # noqa: F401
