# ===================== 存储后端互导（v17.11 U4） =====================
# MySQL ↔ SQLite 搬数据。默认 dry-run，只报告不写。
#
#     python3 scripts/migrate_backend.py                       # 看会搬什么
#     python3 scripts/migrate_backend.py --apply               # 真搬（默认 mysql → sqlite）
#     python3 scripts/migrate_backend.py --to mysql --apply    # 反向
#     python3 scripts/migrate_backend.py --tables cron_tasks,settings --apply
#
# 纪律：
#   - 先备份（脚本开头提示，不自动备份）
#   - 幂等：目标端用 REPLACE / INSERT OR REPLACE，重复跑不会翻倍
#   - 逐表报告行数，不一致就列出

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

BATCH = 500


# ===================== 连接 =====================

def _mysql_conn():
    import pymysql

    from botv.core.constants import DB_CONFIG

    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


def _sqlite_conn(path):
    import sqlite3

    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def connect(backend, sqlite_path=None):
    if backend == "sqlite":
        return _sqlite_conn(sqlite_path)
    return _mysql_conn()


def list_tables(conn, backend):
    c = conn.cursor()
    if backend == "sqlite":
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [r[0] for r in c.fetchall() if not r[0].startswith("sqlite_")]
    c.execute("SHOW TABLES")
    return [list(r.values())[0] for r in c.fetchall()]


def columns(conn, backend, table):
    c = conn.cursor()
    if backend == "sqlite":
        c.execute(f"PRAGMA table_info({table})")
        return [r[1] for r in c.fetchall()]
    c.execute(f"SHOW COLUMNS FROM {table}")
    return [list(r.values())[0] for r in c.fetchall()]


def count(conn, backend, table):
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) FROM {table}")
    row = c.fetchone()
    if isinstance(row, dict):
        return list(row.values())[0]
    return row[0]                      # sqlite3.Row 支持下标


# ===================== 读写 =====================

def read_rows(conn, backend, table, cols, offset=0, limit=BATCH):
    c = conn.cursor()
    col_sql = ", ".join(cols)
    if backend == "sqlite":
        c.execute(f"SELECT {col_sql} FROM {table} LIMIT ? OFFSET ?", (limit, offset))
        return [dict(r) for r in c.fetchall()]
    c.execute(f"SELECT {col_sql} FROM {table} LIMIT %s OFFSET %s", (limit, offset))
    return list(c.fetchall())


def write_rows(conn, backend, table, cols, rows):
    """幂等写入：MySQL 用 REPLACE，SQLite 用 INSERT OR REPLACE"""
    if not rows:
        return 0
    col_sql = ", ".join(cols)
    if backend == "sqlite":
        marks = ", ".join("?" for _ in cols)
        sql = f"INSERT OR REPLACE INTO {table} ({col_sql}) VALUES ({marks})"
        vals = [tuple(r[c] for c in cols) for r in rows]
    else:
        marks = ", ".join("%s" for _ in cols)
        sql = f"REPLACE INTO {table} ({col_sql}) VALUES ({marks})"
        vals = [tuple(r[c] for c in cols) for r in rows]
    c = conn.cursor()
    c.executemany(sql, vals)
    conn.commit()
    return len(rows)


# ===================== 主流程 =====================

def migrate_table(src, src_backend, dst, dst_backend, table, dry=True):
    """搬一张表；返回 (源行数, 搬了几行, 目标行数, 错误)"""
    try:
        src_cols = columns(src, src_backend, table)
        dst_cols = columns(dst, dst_backend, table)
        common = [c for c in src_cols if c in dst_cols]
        if not common:
            return 0, 0, 0, "没有同名列"

        total = count(src, src_backend, table)
        moved = 0
        if not dry:
            for offset in range(0, total, BATCH):
                rows = read_rows(src, src_backend, table, common, offset)
                if not rows:
                    break
                moved += write_rows(dst, dst_backend, table, common, rows)
        dst_total = count(dst, dst_backend, table) if not dry else 0
        return total, moved, dst_total, None
    except Exception as e:
        return 0, 0, 0, str(e)[:80]


def main():
    ap = argparse.ArgumentParser(description="存储后端互导")
    ap.add_argument("--from", dest="src", default="mysql", choices=["mysql", "sqlite"])
    ap.add_argument("--to", dest="dst", default="sqlite", choices=["mysql", "sqlite"])
    ap.add_argument("--sqlite-path", default=None, help="sqlite 文件（默认取配置）")
    ap.add_argument("--tables", default="", help="只搬这些表（逗号分隔）")
    ap.add_argument("--apply", action="store_true", help="真写（默认 dry-run）")
    args = ap.parse_args()

    from botv.core.settings import sqlite_path
    from botv.infra import schema

    path = args.sqlite_path or sqlite_path()
    print("=" * 60)
    print(f"  {args.src} → {args.dst}" + ("" if args.apply else "（dry-run，不写）"))
    print("=" * 60)
    if args.apply:
        print("⚠️  先确认已备份！目标端用 REPLACE 写入，会覆盖同主键的行。\n")

    try:
        src = connect(args.src, path)
        dst = connect(args.dst, path)
    except Exception as e:
        print(f"[X] 连接失败：{e}")
        return 1

    if args.dst == "sqlite":
        print("[准备] 目标端建表…")
        try:
            c = dst.cursor()
            for name, ddl in schema.TABLES.items():
                for stmt in schema.adapt_ddl(ddl, "sqlite"):
                    c.execute(stmt)
            dst.commit()
            print("[准备] 完成\n")
        except Exception as e:
            print(f"[X] 建表失败：{e}")
            return 1

    want = [t.strip() for t in args.tables.split(",") if t.strip()]
    tables = want or [t for t in list_tables(src, args.src) if t in schema.TABLES]

    ok, fail = 0, []
    print(f"{'表':<22}{'源':>8}{'搬':>8}{'目标':>8}")
    print("-" * 48)
    for t in tables:
        src_n, moved, dst_n, err = migrate_table(
            src, args.src, dst, args.dst, t, dry=not args.apply)
        if err:
            print(f"{t:<22}{'-':>8}{'-':>8}{'-':>8}  {err}")
            fail.append((t, err))
            continue
        print(f"{t:<22}{src_n:>8}{moved:>8}{dst_n:>8}")
        ok += 1

    print("-" * 48)
    print(f"成功 {ok} 张，失败 {len(fail)} 张")
    if not args.apply:
        print("\n这是 dry-run。真搬：加 --apply（先备份！）")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
