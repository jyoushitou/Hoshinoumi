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



def step_clock():
    """机器时间与时区检查（v18.0 U6）

    这套代码大量依赖「本地时间 = 东八区」：日志、cron、深夜判断。
    机器若是 UTC，定时会整体偏 8 小时（2026-11-12 实测踩过）。
    """
    import datetime as _dt
    import os as _os

    problems = []
    now_local = _dt.datetime.now()
    now_utc = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    offset = round((now_local - now_utc).total_seconds() / 3600)

    if offset != 8:
        problems.append(f"系统时区 UTC{offset:+d}（应为 UTC+8）")
    if not _os.environ.get("TZ"):
        problems.append("未设置 TZ=Asia/Shanghai")

    # 时钟漂移：拿 HTTP Date 头比（取不到就跳过）
    drift = None
    try:
        import email.utils
        import urllib.request

        resp = urllib.request.urlopen("https://api.deepseek.com", timeout=5)
        date_hdr = resp.headers.get("Date")
        if date_hdr:
            server_ts = email.utils.parsedate_to_datetime(date_hdr)
            drift = abs((now_local - server_ts.astimezone().replace(tzinfo=None)).total_seconds())
            if drift > 120:
                problems.append(f"时钟漂移 {drift:.0f} 秒（>120 秒需校时）")
    except Exception:
        pass

    detail = (f"UTC{offset:+d}｜{now_local.strftime('%Y-%m-%d %H:%M')}"
              + (f"｜漂移 {drift:.0f}s" if drift is not None else "｜漂移未知"))
    if problems:
        raise RuntimeError("；".join(problems) + f"（{detail}）")
    return detail


def step_network():
    """能否连上模型 API（3 秒超时，失败只警告不阻塞）"""
    import socket
    host, port = "api.deepseek.com", 443
    try:
        socket.create_connection((host, port), timeout=3).close()
    except Exception as e:
        raise RuntimeError(f"连不上 {host}:{port}（{type(e).__name__}）")
    return f"{host}:{port} 可达"


def step_env():
    """环境变量一览：只看 NAO_*，值不回显敏感内容"""
    import os
    items = []
    for name in ("NAO_CLIP", "NAO_VOICE", "NAO_VISION_MODEL", "NAO_VISION_URL",
                 "NAO_ASR_URL", "NAO_ASR_MODEL", "NAO_NO_AUTOINSTALL"):
        val = os.getenv(name)
        if val is None:
            items.append(f"{name}=默认")
        elif val.strip() == "":
            items.append(f"{name}=（空，可能有问题）")
        else:
            items.append(f"{name}={val[:40]}")
    return " | ".join(items)


def _has_module(name):
    """模块是否可用（兼容被 stub 进 sys.modules、没有 __spec__ 的情况）"""
    import importlib.util
    import sys
    try:
        return importlib.util.find_spec(name) is not None
    except (ValueError, ImportError):
        return name in sys.modules


def step_capabilities():
    """三块能力现在能不能用（只看依赖，不实际调用）"""
    tts_ok = _has_module("edge_tts")
    pil_ok = _has_module("PIL")

    parts = [f"视觉 {'✅可试' if pil_ok else '⚠️缺PIL（有PIL才能压缩）'}"]
    parts.append(f"语音合成 {'✅' if tts_ok else '⚠️未装 edge-tts（启动会尝试自动装）'}")
    parts.append("语音识别 ✅可试（需服务支持）")
    return " | ".join(parts)


def step_names():
    """静态检查：有没有「用了但没定义」的名字（v10.2）"""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import check_names
    problems = check_names.scan([os.path.join(ROOT, "botv")])
    if problems:
        path, line, name, scope = problems[0]
        raise RuntimeError(
            f"{len(problems)} 处未定义名字，例如 {os.path.basename(path)}:{line} {name}（在 {scope}）"
        )
    return "未定义名字 0 处"


def step_python():
    v = sys.version_info
    if v < (3, 9):
        raise RuntimeError(f"需要 Python ≥ 3.9，当前 {v.major}.{v.minor}")
    return f"{v.major}.{v.minor}.{v.micro} ({sys.executable})"


REQUIRED = ["websockets", "requests", "urllib3", "pymysql", "jieba", "PIL", "aiohttp"]
OPTIONAL = ["chinesecalendar", "torch", "clip", "edge_tts"]
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
    """表是否齐全（v17.5：用 schema.py 的统一表定义）"""
    from botv.infra.conn import get_cursor
    from botv.infra import schema

    c = get_cursor()
    missing = schema.missing_tables(c, schema.REQUIRED)
    if missing:
        raise RuntimeError(
            "缺表: " + ", ".join(missing) +
            "（建表：python3 scripts/init_db.py --apply）")
    return f"{len(set(schema.REQUIRED))} 张必需表齐全"


def step_tables_extra():
    """新表（v17.5 纯表）是否存在——缺了只警告，不阻塞"""
    from botv.infra.conn import get_cursor
    from botv.infra import schema

    c = get_cursor()
    missing = schema.missing_tables(c)
    if missing:
        raise RuntimeError(
            f"还有 {len(missing)} 张表未建（不阻塞）：{', '.join(missing[:5])}…")
    return f"{len(schema.TABLES)} 张表齐全"


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
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--init-db", action="store_true",
                    help="缺表时自动建（等同 scripts/init_db.py --apply）")
    args, _unknown = ap.parse_known_args()

    print("=" * 56)
    print("  友利奈绪 v11 部署预检")
    print("=" * 56)

    if args.init_db:
        try:
            from botv.infra import schema
            made = schema.ensure_tables(log=lambda m: print("  " + m))
            if made:
                print(f"  已自动建表 {len(made)} 张")
        except Exception as _e:
            print(f"  [!] 自动建表失败: {_e}")

    ok_python = check("Python 版本", step_python)
    check("机器时间", step_clock)
    ok_deps = check("必需依赖", step_deps)
    check("代码静态检查", step_names)
    check("环境变量", step_env)
    check("能力自检", step_capabilities)
    check("网络连通", step_network, fatal=False)
    check("可选依赖", step_optional, fatal=False)
    ok_import = check("全模块导入", step_import_all)
    if ok_deps and ok_import:
        check("数据库连接", step_db)
        check("表结构", step_tables)
        check("记忆表结构", step_memory_schema)
        check("新表（v17.5）", step_tables_extra, fatal=False)
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


def _hint():
    print("\n[提示] 这是可选的深度自检；日常部署只需 setup.py + run.py")


if __name__ == "__main__":
    code = main()
    _hint()
    sys.exit(code)
