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


def has_deleted_at(c, table="events"):
    """表里有没有 deleted_at 列（老库没有）"""
    try:
        c.execute(f"SHOW COLUMNS FROM {table} LIKE 'deleted_at'")
        return c.fetchone() is not None
    except Exception:
        return False


def counts(c):
    """各 kind 有多少行（兼容没有 deleted_at 的老表）"""
    where = "WHERE deleted_at IS NULL" if has_deleted_at(c) else ""
    c.execute(f"SELECT kind, COUNT(*) AS n FROM events {where} GROUP BY kind")
    rows = c.fetchall()
    return {r["kind"]: int(r["n"]) for r in rows}


def run_migration():
    """给 setup.py 调用的入口：按真实流程迁一次，返回 (迁移行数, 错误)

    与命令行 `--apply` 等价，但不打印大段表格。
    """
    from bot.infra import schema
    from bot.infra.conn import get_cursor

    c = get_cursor()
    try:
        missing = schema.missing_tables(c)
        if missing:
            return 0, f"缺 {len(missing)} 张新表"

        dist = counts(c)
        total = sum(dist.values())
        if not total:
            return 0, None

        moved = 0
        for kind in [k for k in dist if k in KIND_TO_TABLE]:
            try:
                moved += migrate_json_kind(c, kind) or 0
            except Exception as e:
                return moved, f"{kind}: {e}"
        try:
            migrate_reading(c)
        except Exception:
            pass
        try:
            migrate_habit(c)
        except Exception:
            pass
        return moved, None
    finally:
        try:
            c.close()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的迁移（默认只统计）")
    ap.add_argument("--yes", action="store_true", help="跳过确认")
    args = ap.parse_args()

    from bot.infra.conn import get_cursor
    from bot.infra import schema

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
        alive = "AND deleted_at IS NULL" if has_deleted_at(c) else ""
        sql = f"""
            INSERT IGNORE INTO memories
                (target_id, kind, summary, tags, importance, source,
                 dedupe_key, created_at, last_seen)
            SELECT target_id, %s, event_summary, tags,
                   COALESCE(importance, 3), 'chat',
                   dedupe_key, created_at, last_seen
              FROM events
             WHERE kind = %s {alive}
        """
        try:
            n = c.execute(sql, (kind, kind))
            moved += n if isinstance(n, int) else 0
            print(f"  [OK] {kind} → memories（{n} 行）")
        except Exception as e:
            print(f"  [X] {kind} → memories 失败：{e}")
            return None

    # ---- 其余五类：events 里存的是 JSON（一人一行） ----
    for kind in ("state", "rel", "habit", "reading", "friction"):
        if not dist.get(kind):
            continue
        try:
            if kind == "reading":
                n = migrate_reading(c)
            elif kind == "habit":
                n = migrate_habit(c)
            else:
                n = migrate_json_kind(c, kind)
            moved += n
            print(f"  [OK] {kind} → {JSON_TARGET[kind]}（{n} 行）")
        except Exception as e:
            print(f"  [X] {kind} → {JSON_TARGET[kind]} 失败：{e}")

    try:
        c.connection.commit()
    except Exception:
        pass
    return moved

# ===================== 五类 JSON 数据的迁移 =====================
# 这五类在 events 里都是「一人一行、整段 JSON 存在 event_summary」。
# 迁移 = 取每人最新一行 → 解析 JSON → 按字段名映射到新表。

JSON_TARGET = {
    "state": "bot_states",
    "rel": "relations",
    "habit": "habits",
    "reading": "reading_progress",
    "friction": "friction_states",
}

# 新表允许的字段（不在表里的 JSON 键忽略）
FIELDS = {
    "bot_states": ("target_id", "mood", "energy", "lonely"),
    "relations": ("target_id", "affinity", "since", "tier"),
    "habits": ("target_id", "phrase", "count"),
    "reading_progress": ("target_id", "book_url", "title", "intro",
                         "last_no", "last_chapter"),
    "friction_states": ("target_id", "expect_ts", "expect_text",
                        "disappoint", "cold_ts", "last_grudge"),
}


def _latest_rows(c, kind):
    """每人最新一行（兼容没有 deleted_at 的老表）"""
    alive = "AND deleted_at IS NULL" if has_deleted_at(c) else ""
    c.execute(
        f"SELECT target_id, event_summary FROM events "
        f"WHERE kind=%s {alive} ORDER BY id DESC",
        (kind,),
    )
    seen, out = set(), []
    for r in c.fetchall():
        tid = str(r["target_id"])
        if tid in seen:
            continue
        seen.add(tid)
        out.append((tid, r["event_summary"] or ""))
    return out


def _upsert(c, table, row):
    """按主键覆盖写（INSERT ... ON DUPLICATE KEY UPDATE）"""
    cols = [k for k in row if k in FIELDS[table]]
    if not cols:
        return 0
    if len(cols) <= 1:
        return 0                      # 只有主键，没有可写字段 → 跳过
    placeholders = ",".join(["%s"] * len(cols))
    updates = ",".join(f"{k}=VALUES({k})" for k in cols if k != "target_id")
    head = "INSERT INTO" if updates else "INSERT IGNORE INTO"
    sql = f"{head} {table}({','.join(cols)}) VALUES({placeholders})"
    if updates:
        sql += f" ON DUPLICATE KEY UPDATE {updates}"
    return c.execute(sql, tuple(row[k] for k in cols))


def migrate_json_kind(c, kind):
    """把某一种 JSON 数据搬到新表；返回迁移行数"""
    import json

    table = JSON_TARGET[kind]
    moved = 0
    for tid, payload in _latest_rows(c, kind):
        try:
            data = json.loads(payload) if payload else {}
        except Exception:
            continue                      # 坏 JSON 跳过，不阻塞整批
        if not isinstance(data, dict):
            continue
        row = {"target_id": tid}
        row.update({k: v for k, v in data.items() if k in FIELDS[table]})
        moved += _upsert(c, table, row) or 0
    return moved


def migrate_reading(c):
    """reading 的 JSON 里有 books 列表，一本书一行"""
    import json
    moved = 0
    for tid, payload in _latest_rows(c, "reading"):
        try:
            data = json.loads(payload) if payload else {}
        except Exception:
            continue
        books = data.get("books") if isinstance(data, dict) else None
        if not books:
            continue
        for b in books:
            url = b.get("url") or b.get("book_url")
            if not url:
                continue
            row = {"target_id": tid, "book_url": url,
                   "title": b.get("title"), "last_no": b.get("last_no") or 0,
                   "last_chapter": b.get("last_chapter")}
            moved += _upsert(c, "reading_progress", row) or 0
    return moved


def migrate_habit(c):
    """habit 的 JSON 是 {词: 次数} 或 [词,...]"""
    import json
    moved = 0
    for tid, payload in _latest_rows(c, "habit"):
        try:
            data = json.loads(payload) if payload else {}
        except Exception:
            continue
        pairs = []
        if isinstance(data, dict):
            for key in ("phrases", "words", "counts", "habits"):
                val = data.get(key)
                if isinstance(val, dict):
                    pairs = list(val.items()); break
                if isinstance(val, list):
                    pairs = [(w, 1) for w in val]; break
        if not pairs and isinstance(data, dict):
            # 兜底：顶层直接就是 {词: 次数}
            pairs = [(k, v) for k, v in data.items()
                     if isinstance(v, (int, float))]
        if not pairs and isinstance(data, list):
            pairs = [(w, 1) for w in data if isinstance(w, str)]
        if not pairs:
            continue
        for phrase, count in pairs:
            if not phrase:
                continue
            row = {"target_id": tid, "phrase": str(phrase)[:16],
                   "count": int(count or 1)}
            moved += _upsert(c, "habits", row) or 0
    return moved


def _hint():
    print("\n[提示] 通常不需要单独跑：python3 scripts/setup.py 已包含数据迁移")


if __name__ == "__main__":
    code = main()
    _hint()
    sys.exit(code)
