#!/usr/bin/env python3
# ===================== v8 数据库迁移 =====================
# global_keywords 从「全局唯一」改成「按对象唯一」
#
# 用法：
#     python3 scripts/migrate_v8.py            # 只检查
#     python3 scripts/migrate_v8.py --apply    # 执行
#
# 做三件事：
#   1. 加列 target_id（老数据填 ''，当作「公共词库」）
#   2. 去掉 keyword 上的全局唯一索引
#   3. 加 (target_id, keyword) 联合唯一
#
# 幂等：重复跑不会重复加列/删索引。

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TABLE = "global_keywords"
UK_NAME = "uk_target_keyword"


def has_column(c, table, column):
    c.execute("""
        SELECT COUNT(*) AS n FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s
    """, (table, column))
    return (c.fetchone()["n"] or 0) > 0


def unique_indexes_on(c, table, column):
    c.execute("""
        SELECT INDEX_NAME FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s
          AND COLUMN_NAME=%s AND NON_UNIQUE=0
        GROUP BY INDEX_NAME
    """, (table, column))
    return [r["INDEX_NAME"] for r in c.fetchall()]


def has_index(c, table, name):
    c.execute("""
        SELECT COUNT(*) AS n FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND INDEX_NAME=%s
    """, (table, name))
    return (c.fetchone()["n"] or 0) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--yes", action="store_true")
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
    print("  v8 迁移：global_keywords 按对象隔离" + ("" if args.apply else "（检查模式）"))
    print("=" * 60)

    need_col = not has_column(c, TABLE, "target_id")
    old_uk = [n for n in unique_indexes_on(c, TABLE, "keyword") if n != UK_NAME]
    need_uk = not has_index(c, TABLE, UK_NAME)

    c.execute(f"SELECT COUNT(*) AS n FROM {TABLE}")
    total = c.fetchone()["n"] or 0

    print(f"\n需要加列 target_id：{need_col}")
    print(f"需要删除的旧唯一索引：{old_uk or '无'}")
    print(f"需要加联合唯一索引 {UK_NAME}：{need_uk}")
    print(f"现有词条：{total} 个（迁移后全部归入公共词库 target_id=''）")

    if not (need_col or old_uk or need_uk):
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

    if need_col:
        c.execute(f"ALTER TABLE {TABLE} ADD COLUMN target_id VARCHAR(50) NOT NULL DEFAULT ''")
        print("  ✅ 加列 target_id（老数据默认 ''）")

    for name in old_uk:
        c.execute(f"ALTER TABLE {TABLE} DROP INDEX {name}")
        print(f"  ✅ 删除旧唯一索引 {name}")

    if need_uk:
        c.execute(f"ALTER TABLE {TABLE} ADD UNIQUE KEY {UK_NAME} (target_id, keyword)")
        print(f"  ✅ 加联合唯一索引 {UK_NAME}(target_id, keyword)")

    c.connection.commit()

    c.execute(f"SELECT COUNT(*) AS n FROM {TABLE} WHERE target_id=''")
    legacy = c.fetchone()["n"] or 0
    print(f"\n复查：{TABLE} 共 {total} 条，其中公共词库 {legacy} 条")
    print("✅ 迁移完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
