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

# scene → (时间, 星期, 说明)
SCENES = [
    ("催起床", "07:30", "1,2,3,4,5", "叫我起床"),
    ("周末吐槽赖床", "08:30", "6,7", "吐槽我赖床"),
    ("提醒点外卖", "10:40", "1,2,3,4,5,6,7", "提醒我点外卖"),
    ("叮嘱午睡", "12:30", "1,2,3,4,5,6,7", "提醒我午睡"),
    ("提醒起身", "13:30", "1,2,3,4,5,6,7", "提醒我起身活动"),
    ("提醒晚餐", "18:00", "1,2,3,4,5,6,7", "提醒我吃晚饭"),
    ("催睡觉", "23:00", "1,2,3,4,5,6,7", "催我睡觉"),
    ("周日复盘", "20:00", "7", "跟我复盘这一周"),
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
            existing.add((t.get("schedule_type"), t.get("at_time"),
                          t.get("weekdays"), t.get("content")))
    except Exception as e:
        print(f"[!] 读现有任务失败（可能还没建表）：{e}")
        if args.apply:
            return 1

    created = 0
    for scene, at, days, content in SCENES:
        key = ("weekly", at, days, f"scene:{scene}")
        mark = "已有" if key in existing else "新建"
        print(f"  [{mark}] {at} 周{days} · scene:{scene}（{content}）")
        if not args.apply or key in existing:
            continue
        tid = cron.add(uid, "weekly", f"scene:{scene}", at_time=at,
                       weekdays=days, source="command")
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
