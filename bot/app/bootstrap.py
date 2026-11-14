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


def _check_schema():
    """v21.3：启动只校验 schema_version，绝不建表/改表。"""
    expected = "24"
    try:
        c = get_cursor()
        c.execute("SELECT v FROM bot_meta WHERE k='schema_version'")
        row = c.fetchone()
        actual = str(row["v"]) if row else ""
    except Exception as e:
        raise RuntimeError(
            "数据库结构未初始化或不可读；先运行：python3 scripts/migrate.py --apply"
        ) from e
    if actual != expected:
        raise RuntimeError(
            f"数据库 schema_version={actual or '缺失'}，需要 {expected}；"
            "先运行：python3 scripts/migrate.py --apply"
        )
    log_system(f"[存储] schema_version={actual}")

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
    _check_schema()  # v21.3：启动只校验，不建表/改表
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
