"""v18 U1：迁移脚本（给已存在的 memories 表加 weight / tier）"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

COLUMNS = [
    ("weight", "FLOAT NOT NULL DEFAULT 0.5"),
    ("tier", "VARCHAR(8) NOT NULL DEFAULT 'medium'"),
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的改表（默认只看）")
    args = ap.parse_args()

    from botv.infra.conn import get_cursor

    c = get_cursor()
    try:
        have = _existing(c)
        if not have:
            print("[X] 没有 memories 表（先跑 python3 scripts/setup.py）")
            return 1

        todo = [(name, ddl) for name, ddl in COLUMNS if name not in have]
        print("=" * 56)
        print("  v18.0 · memories 增加记忆分量列")
        print("=" * 56)
        print("现有列:", ", ".join(sorted(have)))
        if not todo:
            print("\n[OK] weight / tier 都已存在，无需迁移")
            return 0

        for name, ddl in todo:
            print(f"\n[..] 待加：{name} {ddl}")
        if not args.apply:
            print("\n这是预览。真改：加 --apply")
            return 0

        for name, ddl in todo:
            c.execute(f"ALTER TABLE memories ADD COLUMN {name} {ddl}")
            print(f"[OK] 已加 {name}")
        c.connection.commit()
        print("\n完成。旧记忆的 weight 默认 0.5（中等），tier 默认 medium。")
        return 0
    finally:
        try:
            c.close()
        except Exception:
            pass


if __name__ == "__main__":
    code = main()
    print("\n[提示] 通常不需要单独跑：python3 scripts/setup.py 会处理")
    sys.exit(code)
