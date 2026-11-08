#!/usr/bin/env python3
# ===================== 表备份 / 还原（无 mysqldump 时用） =====================
# 备份：
#     python3 scripts/backup_table.py events > ~/events-backup.sql
# 还原：
#     python3 scripts/backup_table.py --restore < ~/events-backup.sql
#
# 输出是一行一条 INSERT，方便肉眼检查，也方便按行还原。

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def sql_literal(v):
    """把 Python 值转成 SQL 字面量"""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (bytes, bytearray)):
        return "X'" + bytes(v).hex() + "'"
    if hasattr(v, "isoformat"):  # date / datetime
        return "'" + v.isoformat(sep=" ") + "'" if hasattr(v, "hour") else "'" + v.isoformat() + "'"
    s = str(v).replace("\\", "\\\\").replace("'", "\\'")
    return "'" + s + "'"


def backup(table):
    from botv.infra.conn import get_cursor
    c = get_cursor()
    c.execute(f"SHOW COLUMNS FROM {table}")
    cols = [r["Field"] for r in c.fetchall()]
    if not cols:
        print(f"-- 表 {table} 不存在或没有列", file=sys.stderr)
        return 1

    c.execute(f"SELECT * FROM {table} ORDER BY 1")
    rows = c.fetchall()

    print(f"-- backup: {table}  rows={len(rows)}")
    print("SET NAMES utf8mb4;")
    col_list = ", ".join(cols)
    for r in rows:
        vals = ", ".join(sql_literal(r[col]) for col in cols)
        print(f"INSERT INTO {table} ({col_list}) VALUES ({vals});")
    print(f"-- end: {table}", file=sys.stderr)
    return 0


def restore(wipe=False):
    from botv.infra.conn import get_cursor
    c = get_cursor()
    n = 0
    table = None
    for line in sys.stdin:
        s = line.strip()
        if not s or s.startswith("--") or s.upper().startswith("SET "):
            continue
        if not s.upper().startswith("INSERT"):
            continue
        if table is None:
            # 从 INSERT INTO <表名> 里取表名
            table = s.split("INSERT INTO", 1)[1].split("(", 1)[0].strip()
            if wipe:
                c.execute(f"DELETE FROM {table}")
                c.connection.commit()
                print(f"  已清空 {table}", file=sys.stderr)
        c.execute(s)
        n += 1
        if n % 200 == 0:
            c.connection.commit()
            print(f"  已还原 {n} 行...", file=sys.stderr)
    c.connection.commit()
    print(f"✅ 还原完成：{n} 行", file=sys.stderr)
    return 0


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--restore":
        return restore(wipe="--wipe" in sys.argv)
    if len(sys.argv) < 2:
        print("用法：python3 scripts/backup_table.py <表名> > dump.sql", file=sys.stderr)
        print("     python3 scripts/backup_table.py --restore < dump.sql", file=sys.stderr)
        return 1
    try:
        return backup(sys.argv[1])
    except Exception as e:
        print(f"❌ 备份失败：{type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
