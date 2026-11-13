"""v18 数据迁移（先预览，--apply 才改）

v18.0：memories 加 weight / tier
v18.17：memories 加 due_date / hit_count，kind 放宽为 VARCHAR；
        events 全量复制进 memories，然后改名 events_old_YYYYMMDD，
        最后建只读兼容视图 events（代码读老名字不炸，写路径已切 memories）。

    python3 scripts/migrate_v18.py
    python3 scripts/migrate_v18.py --apply
"""

import argparse
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

COLUMNS = [
    ("weight", "FLOAT NOT NULL DEFAULT 0.5"),
    ("tier", "VARCHAR(8) NOT NULL DEFAULT 'medium'"),
    ("due_date", "DATE NULL"),
    ("hit_count", "INT NOT NULL DEFAULT 0"),
]


def _existing(c, table="memories"):
    """当前列名集合（两种后端）"""
    try:
        c.execute(f"SHOW COLUMNS FROM {table}")
        return {list(r.values())[0] for r in c.fetchall()}
    except Exception:
        pass
    try:
        c.execute(f"PRAGMA table_info({table})")
        return {r["name"] if isinstance(r, dict) else r[1] for r in c.fetchall()}
    except Exception:
        return set()


def _is_sqlite(c):
    try:
        from botv.infra.conn import _SQLiteCursor
        if isinstance(c, _SQLiteCursor):
            return True
    except Exception:
        pass
    try:
        return type(c.connection).__module__ == "sqlite3"
    except Exception:
        return False


def _table_exists(c, table):
    """只认基表；events 兼容视图不能被当成待迁表（迁移要能重复跑）"""
    try:
        if _is_sqlite(c):
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        else:
            c.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema=DATABASE() AND table_name=%s "
                "AND table_type='BASE TABLE'", (table,))
        return bool(c.fetchone())
    except Exception:
        return False


def migrate_columns(c):
    have = _existing(c)
    if not have:
        print("[X] 没有 memories 表（先跑 python3 scripts/setup.py）")
        return 1
    todo = [(name, ddl) for name, ddl in COLUMNS if name not in have]
    print("=" * 56)
    print("  v18.0/v18.17 · memories 列")
    print("=" * 56)
    print("现有列:", ", ".join(sorted(have)))
    if not todo:
        print("[OK] 列都已存在")
        return 0
    for name, ddl in todo:
        print(f"  [缺] {name} {ddl}")
    return len(todo)


def migrate_events(c):
    """events → memories，改名旧表，建兼容视图"""
    print("=" * 56)
    print("  v18.17 · events → memories")
    print("=" * 56)
    if not _table_exists(c, "events"):
        print("[OK] 没有 events 基表（已是视图或已迁移）")
        return 0

    # v18.4 的老 events 表可能没有 deleted_at / due_date / hit_count；
    # 按实际列拼 SELECT，缺的用默认值，别让 ALTER 历史差异卡死迁移。
    cols = _existing(c, "events")
    if not cols:
        print("[X] 读不到 events 列结构")
        return 1
    parts = [
        "target_id",
        "event_summary",
        "tags" if "tags" in cols else "'' AS tags",
        "kind" if "kind" in cols else "'event' AS kind",
        "dedupe_key" if "dedupe_key" in cols else "NULL AS dedupe_key",
        "importance" if "importance" in cols else "3 AS importance",
        "due_date" if "due_date" in cols else "NULL AS due_date",
        "last_seen" if "last_seen" in cols else "NULL AS last_seen",
        "hit_count" if "hit_count" in cols else "0 AS hit_count",
        "created_at" if "created_at" in cols else "CURRENT_TIMESTAMP AS created_at",
        "deleted_at" if "deleted_at" in cols else "NULL AS deleted_at",
    ]
    c.execute("SELECT " + ", ".join(parts) + " FROM events")
    rows = list(c.fetchall())
    print(f"  待迁 {len(rows)} 行")
    sqlite = _is_sqlite(c)
    ph = "?" if sqlite else "%s"
    verb = "INSERT OR IGNORE" if sqlite else "INSERT IGNORE"
    sql = (
        f"{verb} INTO memories(target_id, kind, summary, tags, "
        "importance, weight, tier, source, dedupe_key, due_date, last_seen, "
        "hit_count, created_at, deleted_at) "
        f"VALUES({ph},{ph},{ph},{ph},{ph},0.5,'medium','chat',{ph},{ph},{ph},{ph},{ph},{ph})")
    now = datetime.now()
    for r in rows:
        vals = (r["target_id"], r["kind"] or "event", r["event_summary"],
                r["tags"] or "", r["importance"] or 3, r["dedupe_key"],
                r["due_date"], r["last_seen"], r["hit_count"] or 0,
                r["created_at"] or now, r["deleted_at"])
        try:
            c.execute(sql, vals)
        except Exception as e:
            print(f"  [!] 跳过一行：{e}")
    c.connection.commit()

    old_name = f"events_old_{date.today().strftime('%Y%m%d')}"
    try:
        if _is_sqlite(c):
            c.execute(f"ALTER TABLE events RENAME TO {old_name}")
        else:
            c.execute(f"RENAME TABLE events TO {old_name}")
        c.connection.commit()
        print(f"[OK] 旧表改名为 {old_name}")
    except Exception as e:
        print(f"[!] 旧表改名失败（可能已改名）：{e}")

    # v19.5：不再建 events 兼容视图；应用读路径已全部切 memories
    try:
        c.execute("DROP VIEW IF EXISTS events")
        c.connection.commit()
    except Exception:
        pass
    return 0


def upgrade(c):
    """真正执行 v18.17 迁移（幂等）；不会关闭游标，给 migrate.py 复用"""
    have = _existing(c)
    if not have:
        print("[X] 没有 memories 表")
        return 1
    for name, ddl in COLUMNS:
        if name not in have:
            c.execute(f"ALTER TABLE memories ADD COLUMN {name} {ddl}")
            print(f"[OK] memories 加列 {name}")
    if not _is_sqlite(c):
        try:
            c.execute("ALTER TABLE memories MODIFY kind VARCHAR(16) NOT NULL DEFAULT 'event'")
            print("[OK] memories.kind 放宽为 VARCHAR")
        except Exception:
            pass
    c.connection.commit()
    return migrate_events(c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的改表（默认只看）")
    args = ap.parse_args()

    from botv.infra.conn import get_cursor

    c = get_cursor()
    try:
        n = migrate_columns(c)
        if n == 1 and not _existing(c):
            return 1
        if not args.apply:
            print("\n这是预览。真改：加 --apply")
            return 0
        return upgrade(c)
    finally:
        try:
            c.close()
        except Exception:
            pass


if __name__ == "__main__":
    code = main()
    print("\n[提示] v18.4–v18.16 升级必须先跑本脚本；setup.py 只建缺表，"
          "不会补 memories 列，也不会迁 events。")
    sys.exit(code)
