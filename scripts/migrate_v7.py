#!/usr/bin/env python3
# ===================== v7 数据库迁移 =====================
# 把 events 表从「事件表」扩成「记忆主表」
#
# 用法：
#     python3 scripts/migrate_v7.py            # 只检查，不改（默认）
#     python3 scripts/migrate_v7.py --apply    # 真的执行
#
# 做三件事：
#   1. 加列：kind / dedupe_key / importance / due_date / last_seen / hit_count / embedding
#   2. 回填 dedupe_key = md5(target|kind|归一化文本)
#   3. 合并重复：同 (target, kind, key) 只留最早一条，hit_count 累加
#
# 脚本是幂等的：重复跑不会重复加列、不会误删。

import argparse
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 要加的列：(列名, 定义)
NEW_COLUMNS = [
    ("kind", "VARCHAR(16) NOT NULL DEFAULT 'event'"),
    ("dedupe_key", "CHAR(32) NULL"),
    ("importance", "TINYINT NOT NULL DEFAULT 3"),
    ("due_date", "DATE NULL"),
    ("last_seen", "DATETIME NULL"),
    ("hit_count", "INT NOT NULL DEFAULT 0"),
    ("embedding", "VARBINARY(2048) NULL"),  # v8 向量检索用，先占位
]

# 要加的索引：(索引名, 列)
NEW_INDEXES = [
    ("idx_kind", "target_id, kind"),
    ("idx_dedupe", "dedupe_key"),
]

from botv.infra.dedupe import normalize, dedupe_key  # noqa: E402  共用实现


def column_exists(c, table, column):
    c.execute("""
        SELECT COUNT(*) AS n FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (table, column))
    return (c.fetchone()["n"] or 0) > 0


def index_exists(c, table, index):
    c.execute("""
        SELECT COUNT(*) AS n FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
    """, (table, index))
    return (c.fetchone()["n"] or 0) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的执行（默认只检查）")
    ap.add_argument("--yes", action="store_true", help="跳过确认")
    args = ap.parse_args()

    try:
        from botv.infra.conn import get_cursor
        c = get_cursor()
        c.execute("SELECT 1 AS ok")
        c.fetchone()
    except Exception as e:
        print(f"❌ 连不上数据库：{type(e).__name__}: {e}")
        return 1

    print("=" * 60)
    print("  v7 迁移：events → 记忆主表" + ("" if args.apply else "（检查模式）"))
    print("=" * 60)

    # ---------- 1. 加列 ----------
    missing_cols = [n for n, _ in NEW_COLUMNS if not column_exists(c, "events", n)]
    missing_idx = [n for n, _ in NEW_INDEXES if not index_exists(c, "events", n)]

    print(f"\n缺失的列：{missing_cols or '无'}")
    print(f"缺失的索引：{missing_idx or '无'}")

    # ---------- 2. 统计回填工作量 ----------
    pending = 0
    if "dedupe_key" in missing_cols:
        c.execute("SELECT COUNT(*) AS n FROM events")
        pending = c.fetchone()["n"] or 0
        print(f"待回填 dedupe_key：{pending} 行（新列，全量回填）")
    else:
        c.execute("SELECT COUNT(*) AS n FROM events WHERE dedupe_key IS NULL")
        pending = c.fetchone()["n"] or 0
        print(f"待回填 dedupe_key：{pending} 行")

    # ---------- 3. 统计重复 ----------
    c.execute("""
        SELECT COUNT(*) AS n FROM (
            SELECT target_id, kind, dedupe_key
            FROM events WHERE dedupe_key IS NOT NULL
            GROUP BY target_id, kind, dedupe_key HAVING COUNT(*) > 1
        ) t
    """)
    dup_groups = c.fetchone()["n"] or 0
    c.execute("""
        SELECT COALESCE(SUM(c - 1), 0) AS n FROM (
            SELECT COUNT(*) AS c FROM events WHERE dedupe_key IS NOT NULL
            GROUP BY target_id, kind, dedupe_key HAVING COUNT(*) > 1
        ) t
    """)
    dup_rows = c.fetchone()["n"] or 0
    print(f"重复组：{dup_groups} 组，可合并掉 {dup_rows} 行")

    if not (missing_cols or missing_idx or pending or dup_groups):
        print("\n✅ 已经是最新状态，无需迁移")
        return 0

    if not args.apply:
        print("\n这是检查模式。确认无误后加 --apply 再跑一次。")
        return 0

    if not args.yes:
        ans = input("\n确认执行迁移？输入 yes 继续：").strip().lower()
        if ans != "yes":
            print("已取消")
            return 1

    # ---------- 4. 执行加列 ----------
    for name, ddl in NEW_COLUMNS:
        if name in missing_cols:
            c.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")
            print(f"  ✅ 加列 {name}")
    for name, cols in NEW_INDEXES:
        if name in missing_idx:
            c.execute(f"ALTER TABLE events ADD INDEX {name} ({cols})")
            print(f"  ✅ 加索引 {name}")
    c.connection.commit()

    # ---------- 5. 回填 dedupe_key ----------
    c.execute("SELECT id, target_id, kind, event_summary FROM events WHERE dedupe_key IS NULL")
    rows = c.fetchall()
    for r in rows:
        k = dedupe_key(r["target_id"], r["kind"], r["event_summary"])
        c.execute("UPDATE events SET dedupe_key=%s, last_seen=COALESCE(last_seen, created_at) WHERE id=%s", (k, r["id"]))
    c.connection.commit()
    print(f"  ✅ 回填 dedupe_key：{len(rows)} 行")

    # ---------- 6. 合并重复 ----------
    c.execute("""
        UPDATE events e
        JOIN (
            SELECT target_id, kind, dedupe_key, MIN(id) AS keep_id,
                   COUNT(*) AS c, MAX(created_at) AS last_at
            FROM events
            WHERE dedupe_key IS NOT NULL
            GROUP BY target_id, kind, dedupe_key
            HAVING COUNT(*) > 1
        ) g ON e.id = g.keep_id
        SET e.hit_count = e.hit_count + g.c - 1,
            e.last_seen = g.last_at
    """)
    merged = c.rowcount
    c.execute("""
        DELETE e1 FROM events e1
        JOIN events e2
          ON e1.target_id = e2.target_id
         AND e1.kind = e2.kind
         AND e1.dedupe_key = e2.dedupe_key
         AND e1.id > e2.id
        WHERE e1.dedupe_key IS NOT NULL
    """)
    deleted = c.rowcount
    c.connection.commit()
    print(f"  ✅ 合并：{merged} 组累加计数，删除 {deleted} 条重复")

    # ---------- 7. 复查 ----------
    c.execute("SELECT COUNT(*) AS n FROM events WHERE dedupe_key IS NULL")
    left = c.fetchone()["n"] or 0
    c.execute("SELECT COUNT(*) AS n FROM events")
    total = c.fetchone()["n"] or 0
    print(f"\n复查：events 共 {total} 行，dedupe_key 为空 {left} 行")

    if left:
        print("⚠️ 仍有空 key，请重跑一次")
        return 1
    print("✅ 迁移完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
