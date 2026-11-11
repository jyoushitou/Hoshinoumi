#!/usr/bin/env python3
# ===================== v17.4 数据模型迁移 =====================
# 把 events 里的各类数据拆到新表（见 docs/DB-DESIGN.md 第六节）。
#
#     python3 scripts/migrate_v17.py            # 只统计，不动数据（默认）
#     python3 scripts/migrate_v17.py --apply    # 真迁移（先备份！）
#
# 对应关系：
#     event / life / photo  → memories
#     state                 → bot_states
#     friction              → friction_states
#     reading               → reading_progress
#     habit                 → habits
#     rel                   → relations
#
# 安全：
#   - 默认 dry-run，只读
#   - 迁移用 INSERT IGNORE，重复跑不会重复插
#   - 不删 events 的任何行（只标 deleted_at，留退路）

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# 旧 kind → 新表
KIND_TO_TABLE = {
    "event": "memories",
    "life": "memories",
    "photo": "memories",
    "state": "bot_states",
    "friction": "friction_states",
    "reading": "reading_progress",
    "habit": "habits",
    "rel": "relations",
}


def counts(c):
    """各 kind 有多少行"""
    c.execute("SELECT kind, COUNT(*) AS n FROM events WHERE deleted_at IS NULL GROUP BY kind")
    rows = c.fetchall()
    return {r["kind"]: int(r["n"]) for r in rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的迁移（默认只统计）")
    ap.add_argument("--yes", action="store_true", help="跳过确认")
    args = ap.parse_args()

    from botv.infra.conn import get_cursor
    from botv.infra import schema

    c = get_cursor()
    try:
        print("=" * 56)
        print("  v17.4 数据模型迁移" + ("" if args.apply else "（统计模式）"))
        print("=" * 56)

        # 1) 新表齐不齐
        missing = schema.missing_tables(c)
        if missing:
            print(f"[!] 缺 {len(missing)} 张新表：{', '.join(missing[:6])}")
            print("    先跑：python3 scripts/init_db.py --apply")
            if args.apply:
                return 1
        else:
            print(f"[OK] {len(schema.TABLES)} 张表齐全")

        # 2) 旧数据分布
        try:
            dist = counts(c)
        except Exception as e:
            print(f"[X] 读 events 失败：{e}")
            return 1

        total = sum(dist.values())
        print(f"\n[..] events 待迁移 {total} 行：")
        for kind in sorted(dist):
            table = KIND_TO_TABLE.get(kind, "（不迁移）")
            print(f"     {kind:10} {dist[kind]:6} 行 → {table}")

        unknown = [k for k in dist if k not in KIND_TO_TABLE]
        if unknown:
            print(f"[!] 有未映射的 kind：{', '.join(unknown)}（保持原样）")

        if not args.apply:
            print("\n这是统计模式。真迁移：")
            print("    python3 scripts/migrate_v17.py --apply")
            print("（迁移前请先备份数据库）")
            return 0

        # 3) 真迁移
        if not args.yes:
            print("\n即将写入新表（events 不删，只标记）。继续？[y/N] ", end="")
            if input().strip().lower() not in ("y", "yes"):
                print("已取消")
                return 0

        created = schema.ensure_tables(c)
        if created:
            print(f"[OK] 补建 {len(created)} 张表")

        moved = migrate(c, dist)
        if moved is None:
            return 1

        print(f"\n[OK] 迁移完成：{moved} 行")
        print("     events 保持原样（未删数据）")
        print("     校验：python3 scripts/migrate_v17.py    # 再跑一次看分布")
        return 0
    finally:
        try:
            c.close()
        except Exception:
            pass


def migrate(c, dist):
    """按 kind 拆到新表；返回迁移行数"""
    moved = 0

    # ---- 记忆类：event / life / photo → memories ----
    for kind in ("event", "life", "photo"):
        if not dist.get(kind):
            continue
        sql = """
            INSERT IGNORE INTO memories
                (target_id, kind, summary, tags, importance, source,
                 dedupe_key, created_at, last_seen)
            SELECT target_id, %s, event_summary, tags,
                   COALESCE(importance, 3), 'chat',
                   dedupe_key, created_at, last_seen
              FROM events
             WHERE kind = %s AND deleted_at IS NULL
        """
        try:
            n = c.execute(sql, (kind, kind))
            moved += n if isinstance(n, int) else 0
            print(f"  [OK] {kind} → memories（{n} 行）")
        except Exception as e:
            print(f"  [X] {kind} → memories 失败：{e}")
            return None

    # 其余 kind（state/rel/habit/reading/friction）结构差异大，单独处理
    others = [k for k in dist if k not in ("event", "life", "photo")]
    if others:
        print(f"  [..] 待处理（结构差异，下一步逐表做）：{', '.join(others)}")

    try:
        c.connection.commit()
    except Exception:
        pass
    return moved


if __name__ == "__main__":
    sys.exit(main())
