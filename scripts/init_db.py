#!/usr/bin/env python3
# ===================== 前置建表 =====================
#     python3 scripts/init_db.py             # 只看缺哪些表
#     python3 scripts/init_db.py --apply     # 建缺的（幂等，不动已有表）
#
# 建的表分两类：
#   - 现状表（v7/v8 时代代码正在用）
#   - 新表（docs/DB-DESIGN.md 的纯表，v17.5 逐步切过去）
#
# 全部 CREATE TABLE IF NOT EXISTS，跑一百次也不会破坏数据。

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的建表（默认只看）")
    ap.add_argument("--only", default="", help="只处理这些表（逗号分隔）")
    args = ap.parse_args()

    try:
        from bot.infra.conn import get_cursor
        from bot.infra import schema
    except Exception as e:
        print(f"[X] 导入失败：{e}")
        return 1

    names = [s.strip() for s in args.only.split(",") if s.strip()] or None

    try:
        c = get_cursor()
    except Exception as e:
        print(f"[X] 连不上数据库：{e}")
        print("    检查 config.local.json 里的 DB 配置，或 NAO_DB_* 环境变量")
        return 1

    try:
        missing = schema.missing_tables(c, names)
        print("=" * 56)
        print(f"  表定义 {len(schema.TABLES)} 张，缺 {len(missing)} 张")
        print("=" * 56)
        if not missing:
            print("[OK] 全部已存在，不需要建")
            return 0

        for name in missing:
            print(f"  - {name}")

        if not args.apply:
            print()
            print("这是检查模式。真建表：")
            print("    python3 scripts/init_db.py --apply")
            return 0

        created = schema.ensure_tables(c, names, log=lambda m: print("  [建] " + m))
        print()
        if created:
            print(f"[OK] 建了 {len(created)} 张表：{', '.join(created)}")
        else:
            print("[!] 没有新建（可能刚好被别人建了）")
        return 0
    finally:
        try:
            c.close()
        except Exception:
            pass


def _hint():
    print("\n[提示] 通常不需要单独跑：python3 scripts/setup.py 已包含建表")


if __name__ == "__main__":
    code = main()
    _hint()
    sys.exit(code)
