# ===================== 启动初始化 =====================
# 加载各模块、建表/迁移、初始化运行时状态
# 迁移自 main.py（v5-R5），顺序与逻辑逐字未改

import asyncio
import os

from bot.core import state as cfg
from ..log import log_system, log_err
from ..infra.repo_key import reload_api_keys
from ..infra.conn import get_cursor
from ..memory import load_memories
from ..sticker_archive import init_sticker_archive
from ..clip import init_clip_model
from ..core import tunables  # v15：运行时参数
from ..ai.prompt import load_personality_supplement


def _wire_life():
    """v17.15：注册生活能力端口；失败不阻断启动（ai 侧有默认值）"""
    try:
        from .life_bridge import setup_life_bridge

        names = setup_life_bridge()
        log_system(f"[端口] 生活能力已注册：{len(names)} 项")
    except Exception as e:
        log_err(f"[端口] 注册失败，ai 用默认值：{e}")


def _configure_db():
    """v17.14：把数据库配置注入 infra.conn，断开 conn → settings 的边

    启动时调一次；之后各处 get_cursor() 不再回头读配置。
    """
    try:
        from ..core import settings
        from ..infra import conn

        backend = settings.storage_backend()
        mysql_cfg = settings.db_config() if backend == "mysql" else None
        conn.configure(
            mysql_config=mysql_cfg,
            backend=backend,
            sqlite_path=settings.sqlite_path() if backend == "sqlite" else None,
        )
        log_system(f"[存储] 已注入配置：{backend}")
        return backend
    except Exception as e:
        log_err(f"[存储] 注入配置失败，用默认：{e}")
        return None


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


def _ensure_cron_schema():
    """v18.7：老库补 rule / timing 列 + cron_overrides 表"""
    try:
        from ..infra import schema
        schema.ensure_tables(names=["cron_overrides"])
    except Exception as e:
        log_err(f"[定时] 建 cron_overrides 失败: {e}")
    try:
        c = get_cursor()
        for name, ddl in (("rule", "VARCHAR(16) NULL"),
                          ("timing", "VARCHAR(8) NOT NULL DEFAULT 'exact'")):
            try:
                c.execute(f"ALTER TABLE cron_tasks ADD COLUMN {name} {ddl}")
            except Exception:
                pass  # 已存在
        c.connection.commit()
    except Exception as e:
        log_err(f"[定时] 补 cron_tasks 列失败: {e}")
    try:
        from ..schedule import cron as cron_mod
        cron_mod.migrate_scene_rules()
    except Exception as e:
        log_err(f"[定时] 场景规则迁移失败: {e}")


def _wire_logging():
    """v19.4：把 DB writer 注入 log；log 本身不 import infra/db"""
    try:
        from .. import log as log_mod
        from ..infra.log_sink import write_log_to_db

        log_mod.register_db_writer(write_log_to_db)
    except Exception as e:
        log_err(f"[日志] DB writer 注入失败：{e}")


def bootstrap():
    """同步初始化：加载密钥/记忆/表情包/CLIP/人设，建表，初始化运行时状态"""
    _wire_logging()
    _configure_db()  # v17.14：先把数据库配置注入 infra.conn
    _wire_life()     # v17.15：把 life 能力注册进端口（ai 不 import life）
    reload_api_keys()  # 必须先于 load_memories（追溯日记需要 API key）
    load_memories()  # 从数据库加载对话记忆和全局关键词
    init_sticker_archive()  # 表情包存档目录，迁移旧版 JSON 索引
    if os.getenv("NAO_CLIP") == "1":  # v8-CLIPCUT：默认不加载 CLIP，需要时显式开启
        tunables.load()  # v15：先加载可调参数
    init_clip_model()
    load_personality_supplement()  # 人设补充文本（远程 > 本地）

    # v19.0：启动不再改表；schema 只由 scripts/migrate.py --apply 负责。
    # 缺结构时让后续 SQL 直接报错，由环境监测提前拦住。
    _mark_start()    # v18.5：记录首次启动时间（!uptime 用，不受日志 TTL 影响）

    cfg.PROCESS_LOCK = asyncio.Lock()  # 消息处理锁
    cfg.shutdown_event = asyncio.Event()  # 退出事件（!exit 触发）
    log_system("初始化完成")

def _mark_start():
    """v18.5：记录首次启动时间（用于 !uptime，不受日志 TTL 影响）"""
    try:
        from ..core import version as V
        from ..infra import repo_meta

        first = repo_meta.mark_start(V.get_version())
        if first:
            try:
                from ..log import log_system

                log_system(f"[元数据] 首次启动 {first}")
            except Exception:
                pass
    except Exception:
        pass
