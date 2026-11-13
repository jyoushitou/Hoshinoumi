# ===================== 日记仓储 =====================
# diaries / events / ai_raw_responses 的读取与写入
# 迁移自 diary.py（v5-R5）

from bot.core import state as cfg  # noqa: F401  保持与原模块的副作用一致
from ..infra.conn import get_cursor
from ..log import log_err


def ensure_diaries_table():
    """确保 diaries 表存在（启动时调用，失败不致命）"""
    try:
        c = get_cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS diaries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                target_id VARCHAR(50) NOT NULL,
                diary_date DATE NOT NULL,
                content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_target_date (target_id, diary_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        c.connection.commit()
        return True
    except Exception as e:
        log_err(f"确保 diaries 表存在失败: {e}")
        return False


def get_diary_from_db(target_id: str, date_str: str):
    """从 diaries 表查询已保存的日记，不存在返回 None"""
    try:
        c = get_cursor()
        c.execute(
            "SELECT content FROM diaries WHERE target_id=%s AND diary_date=%s ORDER BY id DESC LIMIT 1",
            (target_id, date_str)
        )
        r = c.fetchone()
        if r and r.get("content"):
            return r["content"]
    except Exception as e:
        log_err(f"查询日记失败({target_id}, {date_str}): {e}")
    return None


def save_diary_to_db(target_id: str, date_str: str, content: str):
    """保存日记到 diaries 表（已存在则更新）"""
    try:
        c = get_cursor()
        c.execute("""
            INSERT INTO diaries (target_id, diary_date, content)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE content=VALUES(content)
        """, (target_id, date_str, content))
        c.connection.commit()
        return True
    except Exception as e:
        log_err(f"保存日记失败({target_id}, {date_str}): {e}")
        return False


def get_events_by_date(target_id: str, date_str: str):
    """查询指定日期的所有事件记录，返回 [(summary, tags)] 列表"""
    try:
        c = get_cursor()
        c.execute(
            "SELECT summary, tags FROM memories WHERE target_id=%s AND DATE(created_at)=%s ORDER BY id",
            (target_id, date_str)
        )
        return [(r["summary"], r.get("tags") or "") for r in c.fetchall()]
    except Exception as e:
        log_err(f"查询事件失败({target_id}, {date_str}): {e}")
        return []


def get_dialogs_by_date(target_id: str, date_str: str, limit=10):
    """查询指定日期的 AI 调用记录（对话素材），返回 [(user_msg, response_text)] 列表"""
    try:
        c = get_cursor()
        c.execute("""
            SELECT user_msg, response_text FROM ai_raw_responses
            WHERE target_id=%s AND DATE(created_at)=%s
              AND response_text IS NOT NULL AND response_text != ''
            ORDER BY id LIMIT %s
        """, (target_id, date_str, limit))
        return [(r["user_msg"] or "", r["response_text"] or "") for r in c.fetchall()]
    except Exception as e:
        log_err(f"查询对话素材失败({target_id}, {date_str}): {e}")
        return []


def get_dates_with_events(target_id: str, limit=7):
    """追溯查询最近有事件记录的 N 个日期（按日期倒序）"""
    try:
        c = get_cursor()
        c.execute("""
            SELECT DISTINCT DATE(created_at) AS d
            FROM memories
            WHERE target_id=%s
            ORDER BY d DESC
            LIMIT %s
        """, (target_id, limit))
        result = []
        for r in c.fetchall():
            d = r["d"]
            # 兼容 date 或 datetime 对象，统一转为 YYYY-MM-DD 字符串
            if hasattr(d, "isoformat"):
                result.append(d.isoformat())
            else:
                result.append(str(d)[:10])
        return result
    except Exception as e:
        log_err(f"追溯查询有事件记录日期失败({target_id}): {e}")
        return []


def count_diaries_of_target(target_id: str) -> int:
    """统计某个目标在 diaries 表中已有的日记数量"""
    try:
        c = get_cursor()
        c.execute("SELECT COUNT(*) AS n FROM diaries WHERE target_id=%s", (target_id,))
        return c.fetchone()["n"] or 0
    except Exception as e:
        log_err(f"统计日记数量失败({target_id}): {e}")
        return 0
