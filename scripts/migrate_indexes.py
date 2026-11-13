"""v18.14：索引清单（幂等，先预览，--apply 才建）

    python3 scripts/migrate_indexes.py          # 只看缺哪些
    python3 scripts/migrate_indexes.py --apply  # 补索引

索引只加在基表；视图不能建索引。已有同名索引就跳过。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 表 → [(索引名, 列)]；只列「查询真的会用到、现有 schema 又没建」的
INDEXES = {
    "events": [("idx_events_target_kind", "target_id, kind, created_at")],
    "ai_raw_responses": [("idx_ai_target_time", "target_id, created_at")],
    "facts": [("idx_facts_target_vis", "target_id, visibility, valid_until")],
}


def _index_names(cursor, table):
    """返回表上已有索引名；表不存在返回 None"""
    try:
        cursor.execute(f"PRAGMA index_list({table})")
        rows = cursor.fetchall()
        if rows:
            return {r["name"] if isinstance(r, dict) else r[1] for r in rows}
        # 空索引表也可能根本没这张表
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            return None
        return set()
    except Exception:
        pass
    try:
        # v18.17：events 已是只读视图，视图不能建索引
        cursor.execute(
            "SELECT table_type AS t FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=%s", (table,))
        row = cursor.fetchone()
        if not row:
            return None
        ttype = row["t"] if isinstance(row, dict) else row[0]
        if str(ttype).upper() != "BASE TABLE":
            return None
    except Exception:
        pass
    try:
        cursor.execute(f"SHOW INDEX FROM {table}")
        rows = cursor.fetchall()
        return {r["Key_name"] if isinstance(r, dict) else r[2] for r in rows}
    except Exception:
        return None


def missing(cursor, indexes=None):
    """[(表, 索引名, 列)]"""
    out = []
    for table, items in (indexes or INDEXES).items():
        have = _index_names(cursor, table)
        if have is None:  # 表还没建
            continue
        for name, cols in items:
            if name not in have:
                out.append((table, name, cols))
    return out


def apply(cursor, indexes=None):
    created = []
    for table, name, cols in missing(cursor, indexes):
        try:
            cursor.execute(f"CREATE INDEX {name} ON {table}({cols})")
            created.append((table, name))
        except Exception as e:
            print(f"  [!] 跳过索引 {name}（{table}）：{e}")
    try:
        cursor.connection.commit()
    except Exception:
        pass
    return created


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的建索引")
    args = ap.parse_args()

    from bot.infra.conn import get_cursor

    c = get_cursor()
    try:
        todo = missing(c)
        print("=" * 56)
        print("  v18.14 · 索引清单")
        print("=" * 56)
        if not todo:
            print("[OK] 需要的索引都在")
            return 0
        for table, name, cols in todo:
            print(f"  [缺] {table}({cols}) → {name}")
        if not args.apply:
            print("\n这是预览。真建：加 --apply")
            return 0
        for table, name in apply(c):
            print(f"[OK] 已建 {name} on {table}")
        return 0
    finally:
        try:
            c.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
