# ===================== 数据库表定义（v17.5 起点 / 前置建表） =====================
# 目的：把「建表」从「跑过的迁移脚本」里拿出来，变成一份**可重复执行**的定义。
#
# 用法：
#     from botv.infra.schema import ensure_tables, missing_tables
#     created = ensure_tables()          # 只建缺的（幂等，不碰已有表）
#
# 什么时候建：
#     - 前置环境检查（scripts/preflight.py --init-db）
#     - 手动：python3 scripts/init_db.py --apply
#     - 启动时 bootstrap 只建 acg_images/diaries（历史原因，保留）
#
# 原则：
#     - 全部 CREATE TABLE IF NOT EXISTS，跑一百次也不会破坏数据
#     - 不改已有表结构（加列走迁移脚本，见 scripts/migrate_*.py）
#     - 新表（v17.5 的纯表）先建出来，代码逐步切过去

# ---------- 现状表（v7/v8 时代，代码正在用） ----------

CURRENT = {
    "logs": """
        CREATE TABLE IF NOT EXISTS logs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            level VARCHAR(16) NOT NULL DEFAULT 'INFO',
            message TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_time (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "api_keys": """
        CREATE TABLE IF NOT EXISTS api_keys (
            key_name VARCHAR(64) PRIMARY KEY,
            key_value VARCHAR(512) NOT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "global_keywords": """
        CREATE TABLE IF NOT EXISTS global_keywords (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            keyword VARCHAR(64) NOT NULL,
            weight DECIMAL(6,3) NOT NULL DEFAULT 1,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_keyword (keyword)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "user_memory": """
        CREATE TABLE IF NOT EXISTS user_memory (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(64) NOT NULL,
            user_msg TEXT,
            bot_msg TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_target_time (target_id, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "events": """
        CREATE TABLE IF NOT EXISTS events (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(64) NOT NULL,
            event_summary VARCHAR(500) NOT NULL,
            tags VARCHAR(200) DEFAULT '',
            kind VARCHAR(16) NOT NULL DEFAULT 'event',
            dedupe_key VARCHAR(128) NULL,
            importance TINYINT NOT NULL DEFAULT 3,
            due_date DATE NULL,
            last_seen DATETIME NULL,
            hit_count INT NOT NULL DEFAULT 0,
            embedding BLOB NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at DATETIME NULL,
            UNIQUE KEY uk_dedupe (target_id, dedupe_key),
            KEY idx_target_time (target_id, created_at),
            KEY idx_kind (kind)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "images": """
        CREATE TABLE IF NOT EXISTS images (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            md5_hash VARCHAR(32) NOT NULL,
            file_path VARCHAR(255) NULL,
            tags VARCHAR(255) DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_md5 (md5_hash)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "ai_raw_responses": """
        CREATE TABLE IF NOT EXISTS ai_raw_responses (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            model_name VARCHAR(64) NULL,
            user_msg TEXT,
            raw_response_json MEDIUMTEXT,
            response_text TEXT,
            target_id VARCHAR(50) NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'success',
            prompt_tokens INT DEFAULT 0,
            completion_tokens INT DEFAULT 0,
            total_tokens INT DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_time (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "acg_images": """
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
    """,
    "diaries": """
        CREATE TABLE IF NOT EXISTS diaries (
            id INT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(50) NOT NULL,
            diary_date DATE NOT NULL,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_target_date (target_id, diary_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
}

# ---------- 新表（docs/DB-DESIGN.md 的纯表，v17.5 逐步切过去） ----------

PURE = {
    "targets": """
        CREATE TABLE IF NOT EXISTS targets (
            target_id VARCHAR(64) PRIMARY KEY,
            kind ENUM('private','group') NOT NULL,
            display_name VARCHAR(64) NULL,
            first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME NULL,
            KEY idx_kind (kind)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "relations": """
        CREATE TABLE IF NOT EXISTS relations (
            target_id VARCHAR(64) PRIMARY KEY,
            affinity DECIMAL(4,3) NOT NULL DEFAULT 0.600,
            since DATE NULL,
            tier VARCHAR(16) NULL,
            daily_gain DECIMAL(4,3) NOT NULL DEFAULT 0,
            gain_day DATE NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "memories": """
        CREATE TABLE IF NOT EXISTS memories (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(64) NOT NULL,
            kind ENUM('event','life','photo','diary_seed') NOT NULL DEFAULT 'event',
            summary VARCHAR(500) NOT NULL,
            tags VARCHAR(200) NULL,
            importance TINYINT NOT NULL DEFAULT 3,
            -- v18.0：记忆分量。weight 0~1（检索排序用），tier 三档（人看的）
            weight FLOAT NOT NULL DEFAULT 0.5,
            tier ENUM('light','medium','heavy') NOT NULL DEFAULT 'medium',
            source ENUM('chat','life','image','manual') NOT NULL DEFAULT 'chat',
            dedupe_key VARCHAR(128) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME NULL,
            deleted_at DATETIME NULL,
            UNIQUE KEY uk_dedupe (target_id, dedupe_key),
            KEY idx_target_time (target_id, created_at),
            KEY idx_kind (kind),
            KEY idx_mem_weight (target_id, weight)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "keywords": """
        CREATE TABLE IF NOT EXISTS keywords (
            target_id VARCHAR(64) NOT NULL,
            keyword VARCHAR(32) NOT NULL,
            weight DECIMAL(6,3) NOT NULL DEFAULT 1,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (target_id, keyword)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "digests": """
        CREATE TABLE IF NOT EXISTS digests (
            target_id VARCHAR(64) NOT NULL,
            day DATE NOT NULL,
            content TEXT NOT NULL,   -- 原来叫 lines，但 LINES 是 MySQL 保留字
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (target_id, day)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "bot_states": """
        CREATE TABLE IF NOT EXISTS bot_states (
            target_id VARCHAR(64) PRIMARY KEY,
            mood DECIMAL(4,3) NOT NULL DEFAULT 0.100,
            energy DECIMAL(4,3) NOT NULL DEFAULT 0.700,
            lonely DECIMAL(4,3) NOT NULL DEFAULT 0.150,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "friction_states": """
        CREATE TABLE IF NOT EXISTS friction_states (
            target_id VARCHAR(64) PRIMARY KEY,
            expect_ts DATETIME NULL,
            expect_text VARCHAR(60) NULL,
            disappoint TINYINT NOT NULL DEFAULT 0,
            cold_ts DATETIME NULL,
            last_grudge DATETIME NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "habits": """
        CREATE TABLE IF NOT EXISTS habits (
            target_id VARCHAR(64) NOT NULL,
            phrase VARCHAR(16) NOT NULL,
            count INT NOT NULL DEFAULT 1,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (target_id, phrase)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "reading_progress": """
        CREATE TABLE IF NOT EXISTS reading_progress (
            target_id VARCHAR(64) NOT NULL,
            book_url VARCHAR(255) NOT NULL,
            title VARCHAR(120) NULL,
            intro VARCHAR(300) NULL,
            last_no INT NOT NULL DEFAULT 0,
            last_chapter VARCHAR(120) NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (target_id, book_url)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "ai_logs": """
        CREATE TABLE IF NOT EXISTS ai_logs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(64) NULL,
            model VARCHAR(64) NULL,
            latency_ms INT NULL,
            ok TINYINT(1) NOT NULL DEFAULT 1,
            err VARCHAR(300) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_time (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "ops_audit": """
        CREATE TABLE IF NOT EXISTS ops_audit (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(64) NULL,
            action VARCHAR(64) NOT NULL,
            command VARCHAR(300) NULL,
            result VARCHAR(300) NULL,
            ok TINYINT(1) NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_time (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "cron_tasks": """
        CREATE TABLE IF NOT EXISTS cron_tasks (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(64) NOT NULL,
            schedule_type ENUM('daily','weekly','once','interval') NOT NULL,
            at_time VARCHAR(16) NULL,                 -- HH:MM
            weekdays VARCHAR(16) NULL,                -- 1,3,5（周一=1）
            once_at DATETIME NULL,                    -- 一次性
            interval_min INT NULL,                    -- 间隔分钟
            content VARCHAR(500) NOT NULL,            -- 要说什么/做什么
            source ENUM('chat','command') NOT NULL DEFAULT 'command',
            enabled TINYINT(1) NOT NULL DEFAULT 1,
            jitter_min TINYINT NOT NULL DEFAULT 10,   -- ±分钟
            rule VARCHAR(16) NULL,                    -- v18.7：wake / sleep / fixed
            timing VARCHAR(8) NOT NULL DEFAULT 'exact',  -- v18.7：exact / habit
            last_fire DATETIME NULL,
            next_ts DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_enabled_next (enabled, next_ts),
            KEY idx_target (target_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "cron_overrides": """
        CREATE TABLE IF NOT EXISTS cron_overrides (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(64) NOT NULL,
            scene VARCHAR(64) NOT NULL,
            day DATE NOT NULL,
            at_time VARCHAR(16) NULL,
            skip TINYINT(1) NOT NULL DEFAULT 0,
            source VARCHAR(16) NOT NULL DEFAULT 'chat',
            note VARCHAR(200) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (target_id, scene, day)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "bot_meta": """
        CREATE TABLE IF NOT EXISTS bot_meta (
            k VARCHAR(64) PRIMARY KEY,
            v VARCHAR(500) NOT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "facts": """
        CREATE TABLE IF NOT EXISTS facts (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            target_id VARCHAR(64) NOT NULL,
            slot VARCHAR(32) NOT NULL,
            value VARCHAR(100) NOT NULL,
            -- v18.4：这条事实是关于谁的 + 能不能公开提
            subject VARCHAR(64) NOT NULL DEFAULT '',
            visibility ENUM('group_ok','private','secret') NOT NULL DEFAULT 'group_ok',
            polarity TINYINT NOT NULL DEFAULT 1,
            valid_from DATETIME NULL,
            valid_until DATETIME NULL,
            confidence FLOAT NOT NULL DEFAULT 0.6,
            source ENUM('chat','manual') NOT NULL DEFAULT 'chat',
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_fact (target_id, slot, value),
            KEY idx_fact_target (target_id, slot)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    "settings": """
        CREATE TABLE IF NOT EXISTS settings (
            k VARCHAR(64) PRIMARY KEY,
            v VARCHAR(500) NOT NULL,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                       ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
}

TABLES = dict(CURRENT)
TABLES.update(PURE)

# 前置检查必须存在的最小集合（现状表；新表缺了不阻塞启动）
REQUIRED = ["logs", "api_keys", "global_keywords", "user_memory",
            "images", "events", "ai_raw_responses", "diaries"]


# ---------- 动作 ----------

def existing_tables(cursor):
    """列出已存在的表名（v17.11：按游标类型判断后端）"""
    from .conn import _SQLiteCursor

    if isinstance(cursor, _SQLiteCursor):
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {row["name"] for row in cursor.fetchall()}
    cursor.execute("SHOW TABLES")
    return {list(row.values())[0] for row in cursor.fetchall()}


def missing_tables(cursor, names=None):
    have = existing_tables(cursor)
    want = names if names is not None else list(TABLES)
    return [n for n in want if n not in have]


def ensure_tables(cursor=None, names=None, log=None):
    """建缺的表；返回实际创建的表名列表

    cursor 不传时自己借一条（用完归还）。
    """
    owned = False
    if cursor is None:
        from .conn import get_cursor

        cursor = get_cursor()
        owned = True

    created = []
    errors = []
    try:
        missing = missing_tables(cursor, names)
        for name in missing:
            ddl = TABLES.get(name)
            if not ddl:
                continue
            try:
                # v17.11：按后端翻译（sqlite 需要改写自增/ENUM/索引）
                for stmt in adapt_ddl(ddl):
                    cursor.execute(stmt)
                created.append(name)
                if log:
                    log(f"建表: {name}")
            except Exception as e:
                # 单张表失败不该拖住其它表：记下来继续
                errors.append((name, str(e)[:120]))
                if log:
                    log(f"[失败] {name}: {str(e)[:120]}")
        # v18.5：视图也要建（方言差异在这里吸收）
        # SQLite 没有 CREATE OR REPLACE：先 DROP 再建，老库里的旧视图定义才会升级
        from .conn import _SQLiteCursor

        sqlite_backend = isinstance(cursor, _SQLiteCursor)
        for vname, vddl in VIEWS.items():
            try:
                if sqlite_backend:
                    cursor.execute(f"DROP VIEW IF EXISTS {vname}")
                cursor.execute(_adapt_view(vddl))
            except Exception as e:
                errors.append((vname, str(e)[:120]))

        if created:
            try:
                cursor.connection.commit()
            except Exception:
                pass
    finally:
        if owned:
            try:
                cursor.close()
            except Exception:
                pass

    if errors:
        import sys as _sys

        print(f"[!] {len(errors)} 张表建失败：" +
              ", ".join(n for n, _ in errors), file=_sys.stderr)
    return created


def describe(cursor=None):
    """给 preflight / !stats 用的一句话"""
    owned = False
    if cursor is None:
        from .conn import get_cursor

        cursor = get_cursor()
        owned = True
    try:
        miss = missing_tables(cursor)
        have = len(TABLES) - len(miss)
        if miss:
            return f"{have}/{len(TABLES)} 张表存在，缺 {len(miss)} 张（{', '.join(miss[:5])}…）"
        return f"{len(TABLES)} 张表齐全"
    finally:
        if owned:
            try:
                cursor.close()
            except Exception:
                pass

# ===================== DDL 方言适配（v17.11） =====================
# 表定义只写一份（MySQL 语法），SQLite 用这个函数现场翻译。
# 只处理这 20 张表里真实用到的写法，不做通用 SQL 解析器。

import re as _re


def _is_sqlite():
    try:
        from ..core.settings import storage_backend

        return storage_backend() == "sqlite"
    except Exception:
        return False


def adapt_ddl(ddl, backend=None):
    """把 MySQL 建表语句翻成目标后端；返回要执行的语句列表

    MySQL 特有、SQLite 不认的部分：
      AUTO_INCREMENT / ENGINE / CHARSET / COMMENT / UNSIGNED /
      ENUM(...) / ON UPDATE CURRENT_TIMESTAMP / 表级 KEY
    """
    backend = backend or ("sqlite" if _is_sqlite() else "mysql")
    if backend != "sqlite":
        return [ddl]

    sql = ddl
    extra = []

    # 1) 表选项（ENGINE=... CHARSET=...）
    sql = _re.sub(r"\)\s*ENGINE=\w+[^;]*$", ")", sql.strip())

    # 2) 整数主键自增
    sql = _re.sub(
        r"(?:BIGINT|INT|INTEGER)\s+AUTO_INCREMENT\s+PRIMARY\s+KEY",
        "INTEGER PRIMARY KEY AUTOINCREMENT", sql, flags=_re.I)
    sql = _re.sub(r"\bBIGINT\b", "INTEGER", sql, flags=_re.I)
    sql = _re.sub(r"\bUNSIGNED\b", "", sql, flags=_re.I)

    # 3) ENUM(...) → TEXT
    sql = _re.sub(r"ENUM\s*\([^)]*\)", "TEXT", sql, flags=_re.I)

    # 4) TINYINT(1) → INTEGER
    sql = _re.sub(r"TINYINT\s*\(\s*1\s*\)", "INTEGER", sql, flags=_re.I)

    # 5) ON UPDATE CURRENT_TIMESTAMP（SQLite 不支持，去掉）
    sql = _re.sub(r"ON\s+UPDATE\s+CURRENT_TIMESTAMP", "", sql, flags=_re.I)

    # 5.5) -- 行注释：必须在压缩空白之前删掉，
    #      否则后面把换行压成空格，整行会被当成注释吞掉（v18.0 踩过）
    sql = _re.sub(r"--[^\n]*", "", sql)

    # 6) COMMENT '...'
    sql = _re.sub(r"\bCOMMENT\s+'[^']*'", "", sql, flags=_re.I)

    # 7) 表级 UNIQUE KEY / KEY / INDEX → 拆成独立 CREATE [UNIQUE] INDEX
    key_re = r",\s*(UNIQUE\s+)?(?:KEY|INDEX)\s+(\w+)\s*\(([^)]*)\)"
    keys = _re.findall(key_re, sql, _re.I)
    if keys:
        table = _re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?", sql, _re.I)
        tname = table.group(1) if table else "t"
        sql = _re.sub(key_re, "", sql, flags=_re.I)
        for unique, idx, cols in keys:
            cols = cols.replace("`", "").replace(" ", "")
            uniq = "UNIQUE " if unique else ""
            extra.append(
                f"CREATE {uniq}INDEX IF NOT EXISTS {idx} ON {tname}({cols})")

    # 8) 收尾：多余逗号、连续空格
    sql = _re.sub(r",\s*,", ",", sql)
    sql = _re.sub(r"\(\s*,", "(", sql)
    sql = _re.sub(r",\s*\)", ")", sql)
    sql = _re.sub(r"[ \t]+", " ", sql)
    sql = sql.strip()

    return [sql] + extra


# ===================== 视图（v18.5） =====================
# 红线：视图不建索引；索引一律建在基表上。
# 视图只做「派生计算」，让上层不用关心方言差异。
#
# v18.5 的教训：**别在视图里用库的 NOW() 算运行时长**。
# MySQL 服务器时区常是 UTC，而 first_start 是应用按东八区写的字符串，
# 两者一减就多 8 小时（L11 同源）。所以另存一份 first_start_ts（epoch），
# 用「当前 epoch − 启动 epoch」算，跨时区、跨方言都对得上。
VIEWS = {
    # 元数据一览：首次启动 / 版本 / 已运行秒数 / 第几天
    "v_bot_meta": """
        CREATE OR REPLACE VIEW v_bot_meta AS
        SELECT
            m.first_start,
            m.first_start_ts,
            m.version,
            CASE WHEN m.first_start_ts IS NULL THEN NULL
                 ELSE UNIX_TIMESTAMP() - m.first_start_ts END AS uptime_seconds,
            CASE WHEN m.first_start_ts IS NULL THEN NULL
                 ELSE CAST((UNIX_TIMESTAMP() - m.first_start_ts) / 86400 AS SIGNED)
            END AS days_since
        FROM (
            SELECT
                (SELECT v FROM bot_meta WHERE k='first_start') AS first_start,
                (SELECT CAST(v AS UNSIGNED) FROM bot_meta WHERE k='first_start_ts')
                    AS first_start_ts,
                (SELECT v FROM bot_meta WHERE k='version') AS version
        ) m
    """,
}

def _adapt_view(ddl):
    """视图方言适配

    MySQL:  CREATE OR REPLACE VIEW ... UNIX_TIMESTAMP() ... CAST(... AS SIGNED)
    SQLite: 没有 CREATE OR REPLACE / UNIX_TIMESTAMP / SIGNED
    """
    try:
        from .conn import _resolve_backend

        backend = _resolve_backend()
    except Exception:
        backend = "mysql"
    if backend != "sqlite":
        return ddl

    out = ddl.replace("CREATE OR REPLACE VIEW", "CREATE VIEW IF NOT EXISTS")
    # epoch 秒：julianday('now') 是 UTC 儒略日，减 1970 的儒略日 = 秒。
    # 注意别写成 strftime('%s','now')：_SQLiteCursor 会把 "%s" 换成 "?"（占位符）。
    out = out.replace(
        "UNIX_TIMESTAMP()",
        "CAST((julianday('now') - 2440587.5) * 86400 AS INTEGER)")
    out = out.replace("AS UNSIGNED", "AS INTEGER")
    out = out.replace("AS SIGNED", "AS INTEGER")
    # 兼容以后视图里可能出现的 NOW()
    out = out.replace("NOW()", "datetime('now','localtime')")
    return out

