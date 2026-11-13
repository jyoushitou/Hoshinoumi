#!/usr/bin/env python3
"""统一迁移入口（推荐部署第一步）

    python3 scripts/migrate.py            # 预览：还缺什么/有多少旧数据
    python3 scripts/migrate.py --apply    # 执行：建表 + 补列 + 迁数据 + 场景 + 索引

幂等：已经迁过的库再跑只会补缺，不会重复搬数据。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


def _preview(c):
    from botv.infra import schema
    from scripts import migrate_v18

    missing = schema.missing_tables(c)
    print(f"  缺表：{', '.join(missing) if missing else '无'}")
    if migrate_v18._table_exists(c, "events"):
        try:
            cols = migrate_v18._existing(c, "events")
            c.execute("SELECT COUNT(*) AS n FROM events")
            n = c.fetchone()["n"]
            print(f"  events 基表：{n} 行；缺列："
                  f"{', '.join(x for x in ('deleted_at', 'due_date', 'hit_count') if x not in cols) or '无'}")
        except Exception as e:
            print(f"  events 读取失败：{e}")
    else:
        print("  events：已是视图或不存在，无需数据迁移")
    mem = migrate_v18._existing(c, "memories")
    if mem:
        need = [x for x in ("weight", "tier", "due_date", "hit_count") if x not in mem]
        print(f"  memories 缺列：{', '.join(need) if need else '无'}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的执行（默认只看）")
    args = ap.parse_args()

    from botv.infra.conn import get_cursor

    c = get_cursor()
    try:
        print("=" * 56)
        print("  v18/v19 数据库迁移")
        print("=" * 56)
        print("当前：")
        if not args.apply:
            return _preview(c)

        from botv.infra import schema
        from scripts import migrate_indexes, migrate_v18, setup

        print("  [1/5] 建缺表")
        made = schema.ensure_tables(c, log=lambda m: print("        " + m))
        print(f"        新建 {len(made)} 张")

        print("  [2/5] 定时表补列 / 场景规则")
        setup.ensure_cron_schema()

        print("  [3/5] v18.17 events → memories")
        rc = migrate_v18.upgrade(c)
        if rc:
            print("[X] 迁移中断，先别启动")
            return rc

        print("  [4/5] 索引")
        try:
            migrate_indexes.apply(c)
        except Exception as e:
            print(f"  [!] 索引补齐失败（不影响启动，可跳过后重试）：{e}")

        print("  [5/5] 内置场景")
        setup.seed_scenes()

        from botv.infra import repo_meta
        repo_meta.set_value("schema_version", "19")
        print("        schema_version=19")
        print("\n[OK] 迁移完成，下一步：python3 checks/env_check.py")
        return 0
    finally:
        try:
            c.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
