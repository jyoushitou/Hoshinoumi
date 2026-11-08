#!/usr/bin/env python3
# ===================== 部署预检 =====================
# 在部署机（7C/12G）上运行：
#     python scripts/preflight.py
# 作用：检查依赖、模块导入、数据库、密钥、表结构，缺什么直接说
# 退出码：0 = 全部通过；1 = 有阻塞项

import importlib
import os
import pkgutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OK, WARN, FAIL = "✅", "⚠️ ", "❌"
results = []


def check(label, fn, fatal=True):
    try:
        detail = fn()
        results.append((OK, label, detail or ""))
        return True
    except Exception as e:
        results.append((FAIL if fatal else WARN, label, f"{type(e).__name__}: {e}"))
        return False


def step_python():
    v = sys.version_info
    if v < (3, 9):
        raise RuntimeError(f"需要 Python ≥ 3.9，当前 {v.major}.{v.minor}")
    return f"{v.major}.{v.minor}.{v.micro} ({sys.executable})"


REQUIRED = ["websockets", "requests", "urllib3", "pymysql", "jieba", "PIL", "aiohttp"]
OPTIONAL = ["chinesecalendar", "torch", "clip"]
# pip 包名 ≠ import 名的映射（否则会误报缺失）
IMPORT_NAME = {"chinesecalendar": "chinese_calendar", "PIL": "PIL", "clip": "clip"}


def _import(name):
    return importlib.import_module(IMPORT_NAME.get(name, name))


def step_deps():
    missing = []
    for name in REQUIRED:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    if missing:
        raise RuntimeError("缺少必需依赖: " + ", ".join(missing))
    return f"{len(REQUIRED)} 个必需依赖齐全"


def step_optional():
    missing = []
    for name in OPTIONAL:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    if missing:
        return f"未安装: {', '.join(missing)}（功能会降级，不阻塞）"
    return "全部已安装"


def step_import_all():
    import botv
    mods = ["botv"]
    for m in pkgutil.walk_packages(botv.__path__, "botv."):
        mods.append(m.name)
    failed = []
    for name in mods:
        try:
            importlib.import_module(name)
        except Exception as e:
            failed.append(f"{name}: {type(e).__name__}: {e}")
    if failed:
        raise RuntimeError("导入失败: " + " | ".join(failed[:3]))
    return f"{len(mods)} 个模块全部导入成功"


def step_db():
    from botv.infra.conn import get_cursor
    c = get_cursor()
    c.execute("SELECT 1 AS ok")
    r = c.fetchone()
    if not r or r.get("ok") != 1:
        raise RuntimeError("SELECT 1 返回异常")
    from botv.core.constants import DB_CONFIG
    return f"{DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"


def step_tables():
    from botv.infra.conn import get_cursor
    expected = ["logs", "api_keys", "global_keywords", "user_memory",
                "images", "events", "ai_raw_responses", "diaries"]
    c = get_cursor()
    c.execute("SHOW TABLES")
    existing = {list(row.values())[0] for row in c.fetchall()}
    missing = [t for t in expected if t not in existing]
    if missing:
        raise RuntimeError("缺表: " + ", ".join(missing))
    return f"{len(expected)} 张表齐全"


def step_memory_schema():
    """v7：events 是否已扩成记忆主表"""
    from botv.infra.conn import get_cursor
    need_cols = ["kind", "dedupe_key", "importance", "due_date",
                 "last_seen", "hit_count", "embedding"]
    need_idx = ["idx_kind", "idx_dedupe"]

    c = get_cursor()
    c.execute("SHOW COLUMNS FROM events")
    cols = {r["Field"] for r in c.fetchall()}
    missing = [x for x in need_cols if x not in cols]
    if missing:
        raise RuntimeError("events 缺列: " + ", ".join(missing) + "（跑 scripts/migrate_v7.py --apply）")

    c.execute("SHOW INDEX FROM events")
    idx = {r["Key_name"] for r in c.fetchall()}
    missing_idx = [x for x in need_idx if x not in idx]
    if missing_idx:
        raise RuntimeError("events 缺索引: " + ", ".join(missing_idx))

    c.execute("SELECT COUNT(*) AS n FROM events WHERE dedupe_key IS NULL")
    nulls = c.fetchone()["n"] or 0
    if nulls:
        raise RuntimeError(f"{nulls} 行 dedupe_key 为空（重跑迁移脚本）")

    c.execute("SELECT kind, COUNT(*) AS n FROM events GROUP BY kind")
    rows = c.fetchall()
    dist = ", ".join(f"{r['kind']}={r['n']}" for r in rows) if rows else "空表"
    return f"7 列 + 2 索引齐全 · {dist}"


def step_keys():
    from botv.infra.repo_key import get_api_key_from_db
    keys = {name: bool(get_api_key_from_db(name)) for name in ("DS_API_KEY", "ARK_API_KEY", "ALAPI_TOKEN")}
    missing = [k for k, v in keys.items() if not v]
    if missing:
        raise RuntimeError("缺密钥: " + ", ".join(missing))
    return "DS / 豆包 / ALAPI 均已配置"


def step_prompt():
    from botv.ai.prompt import get_system_prompt, load_personality_supplement
    load_personality_supplement()
    p = get_system_prompt()
    if "{available_tags}" in p:
        raise RuntimeError("标签占位符未被替换")
    return f"system prompt {len(p)} 字"


def main():
    print("=" * 56)
    print("  友利奈绪 v8 部署预检")
    print("=" * 56)

    ok_python = check("Python 版本", step_python)
    ok_deps = check("必需依赖", step_deps)
    check("可选依赖", step_optional, fatal=False)
    ok_import = check("全模块导入", step_import_all)
    if ok_deps and ok_import:
        check("数据库连接", step_db)
        check("表结构", step_tables)
        check("记忆表结构", step_memory_schema)
        check("API 密钥", step_keys)
        check("人设提示词", step_prompt)
    else:
        results.append((WARN, "数据库等", "依赖或导入未通过，后续检查已跳过"))

    print()
    for icon, label, detail in results:
        print(f"{icon} {label:<10} {detail}")

    failed = [r for r in results if r[0] == FAIL]
    print()
    if failed:
        print(f"共 {len(failed)} 项阻塞，修完再启动。")
        return 1
    print("全部通过，可以启动：python run.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
