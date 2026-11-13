#!/usr/bin/env python3
# ===================== 兜底数据清理 =====================
# v5-F2 配套：清掉历史上写进数据库的兜底文案
#
# 用法：
#     python scripts/clean_fallback_data.py            # 只统计，不删（默认）
#     python scripts/clean_fallback_data.py --apply    # 真的删
#     python scripts/clean_fallback_data.py --apply --yes   # 跳过确认
#
# 清理三张表：
#   user_memory      —— bot_msg 是兜底文案的行
#   events           —— event_summary 是兜底文案的行
#   global_keywords  —— 由兜底文案污染出来的词
# 另外做一次 user_memory 的完全重复行去重（保留最新一条）

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 历史上会被写进库的兜底文案
FALLBACK_TEXTS = [
    "哼(扭头)",
    "才不理你(抱手)",
    "切(翻白眼)",
    "嗯嗯(点头)",
    "（无）",
    "(无)",
    "……",
]

# 从兜底文案里被 jieba 提炼出来的垃圾关键词
JUNK_KEYWORDS = ["扭头", "抱手", "翻白眼", "点头", "嗯", "哼", "切"]


def _placeholders(items):
    return ",".join(["%s"] * len(items))


def count_rows(c, table, column, values):
    c.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {column} IN ({_placeholders(values)})", values)
    return c.fetchone()["n"] or 0


def sample_rows(c, table, column, values, extra="", limit=5):
    c.execute(f"SELECT * FROM {table} WHERE {column} IN ({_placeholders(values)}) {extra} LIMIT {limit}", values)
    return c.fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的执行删除（默认只统计）")
    ap.add_argument("--yes", action="store_true", help="跳过交互确认")
    args = ap.parse_args()

    try:
        from botv.infra.conn import get_cursor
        c = get_cursor()
        c.execute("SELECT 1 AS ok")
        c.fetchone()
    except Exception as e:
        print(f"❌ 连不上数据库：{type(e).__name__}: {e}")
        print("   请在部署机上运行（或先确认 core/constants.py 里的 DB_CONFIG）")
        return 1

    print("=" * 60)
    print("  兜底数据清理" + ("" if args.apply else "（统计模式，不会删除）"))
    print("=" * 60)

    mem_n = count_rows(c, "user_memory", "bot_msg", FALLBACK_TEXTS)
    evt_n = count_rows(c, "events", "event_summary", FALLBACK_TEXTS)
    kw_n = count_rows(c, "global_keywords", "keyword", JUNK_KEYWORDS)

    c.execute("""
        SELECT COUNT(*) AS n FROM (
            SELECT target_id, user_msg, bot_msg
            FROM user_memory
            GROUP BY target_id, user_msg, bot_msg
            HAVING COUNT(*) > 1
        ) AS dup
    """)
    dup_n = c.fetchone()["n"] or 0

    print(f"\nuser_memory     兜底行 : {mem_n} 条")
    print(f"events          兜底行 : {evt_n} 条")
    print(f"global_keywords 垃圾词 : {kw_n} 个")
    print(f"user_memory     重复组 : {dup_n} 组（每组保留最新一条）")

    if mem_n:
        print("\n样例（user_memory）：")
        for r in sample_rows(c, "user_memory", "bot_msg", FALLBACK_TEXTS):
            print(f"  id={r['id']} target={r['target_id']} bot={r['bot_msg'][:20]!r}")

    if kw_n:
        c.execute(f"SELECT keyword FROM global_keywords WHERE keyword IN ({_placeholders(JUNK_KEYWORDS)})", JUNK_KEYWORDS)
        print("\n垃圾词：", "、".join(r["keyword"] for r in c.fetchall()))

    if not any([mem_n, evt_n, kw_n, dup_n]):
        print("\n✅ 没有需要清理的数据")
        return 0

    if not args.apply:
        print("\n这是统计模式。要真的删除，加上 --apply 再跑一次。")
        return 0

    if not args.yes:
        ans = input("\n确认删除以上数据？输入 yes 继续：").strip().lower()
        if ans != "yes":
            print("已取消")
            return 1

    # ---- 执行删除 ----
    print("\n开始清理...")

    c.execute(f"DELETE FROM user_memory WHERE bot_msg IN ({_placeholders(FALLBACK_TEXTS)})", FALLBACK_TEXTS)
    print(f"  ✅ user_memory 删除兜底行: {c.rowcount}")

    c.execute(f"DELETE FROM memories WHERE summary IN ({_placeholders(FALLBACK_TEXTS)})", FALLBACK_TEXTS)
    print(f"  ✅ events 删除兜底行: {c.rowcount}")

    c.execute(f"DELETE FROM global_keywords WHERE keyword IN ({_placeholders(JUNK_KEYWORDS)})", JUNK_KEYWORDS)
    print(f"  ✅ global_keywords 删除垃圾词: {c.rowcount}")

    # 去重：同 target + 同 user_msg + 同 bot_msg 只留 id 最大的一条
    c.execute("""
        DELETE t1 FROM user_memory t1
        JOIN user_memory t2
          ON t1.target_id = t2.target_id
         AND t1.user_msg  = t2.user_msg
         AND t1.bot_msg   = t2.bot_msg
         AND t1.id < t2.id
    """)
    print(f"  ✅ user_memory 去重删除: {c.rowcount}")

    c.connection.commit()
    print("\n已提交。")

    # ---- 复查 ----
    mem_n2 = count_rows(c, "user_memory", "bot_msg", FALLBACK_TEXTS)
    evt_n2 = count_rows(c, "events", "event_summary", FALLBACK_TEXTS)
    kw_n2 = count_rows(c, "global_keywords", "keyword", JUNK_KEYWORDS)
    print(f"复查：user_memory={mem_n2}  events={evt_n2}  keywords={kw_n2}")
    return 0 if not any([mem_n2, evt_n2, kw_n2]) else 1


if __name__ == "__main__":
    sys.exit(main())

