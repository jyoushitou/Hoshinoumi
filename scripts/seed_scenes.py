# ===================== 旧场景 → cron_tasks 迁移（v17.7） =====================
# 把写死在 SCHEDULE_TASKS 里的 8 个场景，变成 cron_tasks 里的数据。
#
#   python3 scripts/seed_scenes.py            # 只看会建哪些
#   python3 scripts/seed_scenes.py --apply    # 写进库
#
# 只建一次（按 content 去重），重复跑不会重复插。
#
# 迁移后：
#   - ticker 的 SCHEDULE_TASKS 派发可以删（下一版）
#   - 场景仍在 executors/schedule.py 里（提示词表），只是触发改成 cron

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# v18.7：scene → (rule, 时间, 星期, timing, jitter, 说明)
SCENES = [
    ("催起床", "wake", None, None, "habit", 5, "叫我起床"),
    ("催睡觉", "sleep", None, None, "habit", 3, "催我睡觉"),
    ("提醒点外卖", None, "10:40", None, "habit", 5, "提醒我点外卖"),
    ("叮嘱午睡", None, "12:30", None, "habit", 2, "提醒我午睡"),
    ("叫午睡起床", None, "13:30", None, "exact", 0, "叫我午睡起来"),
    ("提醒晚餐", None, "16:40", None, "habit", 2, "提醒我吃晚饭"),
    ("周日复盘", None, "21:00", "7", "exact", 0, "跟我复盘这一周"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真的写库（默认只预览）")
    args = ap.parse_args()

    try:
        from botv.core import state as cfg
        from botv.schedule import cron
    except Exception as e:
        print(f"[X] 导入失败：{e}")
        return 1

    uid = str(cfg.MASTER_QQ)
    print("=" * 56)
    print("  场景 → cron_tasks" + ("" if args.apply else "（预览）"))
    print("=" * 56)
    print(f"目标：{uid}\n")

    existing = set()
    try:
        for t in cron.list_tasks(uid):
            existing.add(t.get("content"))
    except Exception as e:
        print(f"[!] 读现有任务失败（可能还没建表）：{e}")
        if args.apply:
            return 1

    created = 0
    for scene, rule, at, days, timing, jitter, content in SCENES:
        key = f"scene:{scene}"
        mark = "已有" if key in existing else "新建"
        when = "规则" if rule else (f"周{days} {at}" if days else at)
        print(f"  [{mark}] {when} · {key}（{content}）")
        if not args.apply or key in existing:
            continue
        stype = "weekly" if days else "daily"
        tid = cron.add(uid, stype, key, at_time=at, weekdays=days,
                       source="command", jitter_min=jitter,
                       rule=rule, timing=timing)
        if tid:
            created += 1

    print()
    if args.apply:
        print(f"[OK] 新建 {created} 条；重启或等 04:00 对账后生效")
        print("     验证：!cron")
    else:
        print("这是预览。真写库：")
        print("    python3 scripts/seed_scenes.py --apply")
    return 0


def _hint():
    print("\n[提示] 通常不需要单独跑：python3 scripts/setup.py 已包含场景导入")


if __name__ == "__main__":
    code = main()
    _hint()
    sys.exit(code)
