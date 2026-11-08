# ===================== 启动初始化 =====================
# 加载各模块、建表/迁移、初始化运行时状态
# 迁移自 main.py（v5-R5），顺序与逻辑逐字未改

import asyncio
import os

from botv.core import state as cfg
from ..log import log_system, log_err
from ..infra.repo_key import reload_api_keys
from ..infra.conn import get_cursor
from ..memory import load_memories
from ..sticker_archive import init_sticker_archive
from ..clip import init_clip_model
from ..ai.prompt import load_personality_supplement


def _ensure_tables():
    """确保 acg_images / diaries 表存在，并给 ai_raw_responses 补 token 字段"""
    # 确保 ACG 图片表存在（用于缓存 ACG 二次元图片）
    try:
        c = get_cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS acg_images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                md5_hash VARCHAR(32) NOT NULL UNIQUE,
                image_data MEDIUMBLOB,
                tags VARCHAR(255) DEFAULT '',
                source_url VARCHAR(512) DEFAULT '',
                file_path VARCHAR(255) DEFAULT '',
                ext VARCHAR(10) DEFAULT 'jpg',
                use_count INT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        c.connection.commit()
        log_system("acg_images 表已就绪")
    except Exception as e:
        log_err(f"建表失败: {e}")

    # 确保 diaries 日记表存在（用于存储自动生成的日记）
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
        log_system("diaries 表已就绪")
    except Exception as e:
        log_err(f"创建 diaries 表失败: {e}")

    # 确保 ai_raw_responses 表有 token 用量字段（数据库迁移）
    try:
        c = get_cursor()
        c.execute("SHOW COLUMNS FROM ai_raw_responses LIKE 'prompt_tokens'")
        if not c.fetchone():  # 字段不存在，执行迁移
            c.execute("ALTER TABLE ai_raw_responses ADD COLUMN prompt_tokens INT DEFAULT 0")
            c.execute("ALTER TABLE ai_raw_responses ADD COLUMN completion_tokens INT DEFAULT 0")
            c.execute("ALTER TABLE ai_raw_responses ADD COLUMN total_tokens INT DEFAULT 0")
            c.connection.commit()
            log_system("ai_raw_responses 表已升级，添加token用量字段")
        else:
            log_system("ai_raw_responses 表token字段已存在")
    except Exception as e:
        log_err(f"升级ai_raw_responses表失败: {e}")


def bootstrap():
    """同步初始化：加载密钥/记忆/表情包/CLIP/人设，建表，初始化运行时状态"""
    reload_api_keys()  # 必须先于 load_memories（追溯日记需要 API key）
    load_memories()  # 从数据库加载对话记忆和全局关键词
    init_sticker_archive()  # 表情包存档目录，迁移旧版 JSON 索引
    if os.getenv("NAO_CLIP") == "1":  # v8-CLIPCUT：默认不加载 CLIP，需要时显式开启
        init_clip_model()
    load_personality_supplement()  # 人设补充文本（远程 > 本地）

    _ensure_tables()

    cfg.PROCESS_LOCK = asyncio.Lock()  # 消息处理锁
    cfg.shutdown_event = asyncio.Event()  # 退出事件（!exit 触发）
    log_system("初始化完成(CLIP识图版)")
