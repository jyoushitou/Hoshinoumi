#!/usr/bin/env python3
# ===================== 环境初始化（建表前置） =====================
# 一个脚本把「跑起来之前要做的两件事」做完：
#
#     python3 scripts/setup.py            # 一条命令：装缺的依赖 + 建缺的表
#     python3 scripts/setup.py --check    # 只检查，不动环境
#
# 拉下来之后只需要两条命令：
#     python3 scripts/setup.py && python3 run.py
#
# 顺序刻意如此：
#   1. 依赖：没有 pymysql 连数据库都 import 不了
#   2. 建表：没有表，启动第一步 SHOW TABLES 就失败
#
# 之后才是 preflight（更全面的自检）和 run.py（启动）：
#
#     setup.py → run.py（就这两条；preflight 等属可选排查）

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

# import 名 → pip 包名
REQUIRED = {
    "websockets": "websockets",
    "requests": "requests",
    "pymysql": "pymysql",
    "jieba": "jieba",
    "PIL": "Pillow",
    "aiohttp": "aiohttp",
}
OPTIONAL = {
    "chinese_calendar": "chinesecalendar",
    "edge_tts": "edge-tts",
}

MIN_PYTHON = (3, 10)


def check_python():
    ok = sys.version_info >= MIN_PYTHON
    ver = ".".join(map(str, sys.version_info[:3]))
    print(f"  {'[OK]' if ok else '[X] '} Python {ver}")
    return ok


def _missing(deps):
    out = []
    for mod, pkg in deps.items():
        try:
            __import__(mod)
        except ImportError:
            out.append((mod, pkg))
    return out


def check_deps(install=False):
    missing = _missing(REQUIRED)
    if not missing:
        print(f"  [OK] 必需依赖 {len(REQUIRED)} 个齐全")
        return True

    names = ", ".join(pkg for _, pkg in missing)
    print(f"  [X]  缺依赖：{names}")
    if not install:
        print("       运行 python3 scripts/setup.py 会自动安装")
        return False

    print("       正在安装……")
    cmd = [sys.executable, "-m", "pip", "install", *[pkg for _, pkg in missing]]
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print("       [!] pip 安装失败。Debian/Ubuntu 可能需要：")
        print("           python3 -m pip install --user --break-system-packages " + " ".join(
            pkg for _, pkg in missing))
        return False

    still = _missing(REQUIRED)
    if still:
        print("       [X] 装完仍缺：" + ", ".join(p for _, p in still))
        return False
    print("       [OK] 依赖安装完成")
    return True


def check_optional():
    miss = _missing(OPTIONAL)
    if miss:
        print(f"  [!]  可选依赖未装：{', '.join(p for _, p in miss)}（降级运行）")
    else:
        print(f"  [OK] 可选依赖 {len(OPTIONAL)} 个齐全")
    return True


def init_tables():
    """建缺的表（幂等）"""
    try:
        from bot.infra import schema
        from bot.infra.conn import get_cursor
    except Exception as e:
        print(f"  [X] 无法导入数据库模块：{e}")
        return False

    try:
        c = get_cursor()
    except Exception as e:
        print(f"  [X] 连不上数据库：{e}")
        print("       检查 config.local.json 的 DB 配置（或 NAO_DB_* 环境变量）")
        return False

    try:
        missing = schema.missing_tables(c)
        if not missing:
            print(f"  [OK] {len(schema.TABLES)} 张表齐全")
            return True
        print(f"  [..] 缺 {len(missing)} 张表，开始建")
        created = schema.ensure_tables(c, log=lambda m: print("       " + m))
        left = schema.missing_tables(c)
        if left:
            print(f"  [!]  还有 {len(left)} 张没建成：{', '.join(left)}")
            return False
        print(f"  [OK] 建了 {len(created)} 张表")
        return True
    finally:
        try:
            c.close()
        except Exception:
            pass


def migrate_data():
    """把旧表里的数据搬进新表（幂等：搬过就不会重复搬）"""
    try:
        from bot.infra import schema
        from bot.infra.conn import get_cursor
    except Exception as e:
        print(f"  [!]  跳过迁移（导入失败）：{e}")
        return True

    try:
        c = get_cursor()
    except Exception as e:
        print(f"  [!]  跳过迁移（连不上库）：{e}")
        return True

    try:
        # 新表还没建好就别迁
        have = schema.existing_tables(c)
        need = {"memories", "bot_states", "relations"}
        if not need.issubset(have):
            print("  [!]  新表不全，跳过数据迁移")
            return True

        # v19.5：events 兼容视图已删除；旧数据迁移由 scripts/migrate.py 负责
        legacy = 0
        c.execute("SELECT COUNT(*) AS n FROM memories")
        migrated = list(c.fetchone().values())[0]

        if legacy == 0:
            print("  [OK] 旧表没有数据，无需迁移")
            return True
        if migrated > 0:
            print(f"  [OK] 已迁移过（memories {migrated} 行），跳过")
            return True

        print(f"  [..] 检测到旧数据 {legacy} 行，开始迁移")
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import importlib

        m = importlib.import_module("scripts.migrate_v17")
        moved, err = m.run_migration()
        if err:
            print(f"  [!]  迁移中断：{err}")
        else:
            print(f"  [OK] 迁移完成（{moved} 行）")
        return True
    except Exception as e:
        print(f"  [!]  迁移失败（不影响启动，可手动跑 migrate_v17.py）：{e}")
        return True
    finally:
        try:
            c.close()
        except Exception:
            pass


def ensure_cron_schema():
    """v18.7：setup 阶段补 cron_tasks.rule/timing + 场景规则迁移

    不能只依赖 bootstrap：seed_scenes 在 run.py 之前跑，旧库还没补列。
    """
    try:
        from bot.infra import schema
        from bot.infra.conn import get_cursor
    except Exception as e:
        print(f"  [!]  跳过定时表补列（导入失败）：{e}")
        return True

    try:
        schema.ensure_tables(names=["cron_overrides"])
        c = get_cursor()
        try:
            for name, ddl in (("rule", "VARCHAR(16) NULL"),
                              ("timing", "VARCHAR(8) NOT NULL DEFAULT 'exact'")):
                try:
                    c.execute(f"ALTER TABLE cron_tasks ADD COLUMN {name} {ddl}")
                    print(f"  [OK] cron_tasks 补列 {name}")
                except Exception:
                    pass  # 已存在
            c.connection.commit()
            try:
                from bot.schedule import cron
                cron.migrate_scene_rules()
            except Exception as e:
                print(f"  [!]  场景规则迁移失败（启动时会再试）：{e}")
            return True
        finally:
            try:
                c.close()
            except Exception:
                pass
    except Exception as e:
        print(f"  [!]  定时表补列失败（启动时会再试）：{e}")
        return True


def seed_scenes():
    """把内置 8 个场景写进 cron_tasks（幂等：按内容去重）"""
    try:
        from bot.core import state as cfg
        from bot.schedule import cron
    except Exception as e:
        print(f"  [!]  跳过场景导入（导入失败）：{e}")
        return True

    try:
        uid = str(cfg.MASTER_QQ)
        if not uid:
            print("  [--] 没配 master_qq，跳过场景导入")
            return True

        # v18.7：规则化种子；已有旧行由 cron.migrate_scene_rules() 原地修正
        scenes = [
            # scene, rule, at_time, weekdays, timing, jitter
            ("催起床", "wake", None, None, "habit", 5),
            ("催睡觉", "sleep", None, None, "habit", 3),
            ("提醒点外卖", None, "10:40", None, "habit", 5),
            ("叮嘱午睡", None, "12:30", None, "habit", 2),
            ("叫午睡起床", None, "13:30", None, "exact", 0),
            ("提醒晚餐", None, "16:40", None, "habit", 2),
            ("周日复盘", None, "21:00", "7", "exact", 0),
        ]
        existing = {row.get("content") for row in cron.list_tasks(uid)}

        created = 0
        for scene, rule, at, days, timing, jitter in scenes:
            content = f"scene:{scene}"
            if content in existing:
                continue
            stype = "weekly" if days else "daily"
            if cron.add(uid, stype, content, at_time=at, weekdays=days,
                        source="command", jitter_min=jitter,
                        rule=rule, timing=timing):
                created += 1
        if created:
            print(f"  [OK] 导入 {created} 个内置场景")
        else:
            print("  [OK] 内置场景已存在")
        return True
    except Exception as e:
        print(f"  [!]  场景导入失败（不影响启动）：{e}")
        return True



def check_clock():
    """机器时间检查（v18.0 U6）：只提示，不阻塞"""
    import datetime as _dt

    now_local = _dt.datetime.now()
    now_utc = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    offset = round((now_local - now_utc).total_seconds() / 3600)
    if offset != 8:
        print(f"  [!]  机器时区是 UTC{offset:+d}，不是 UTC+8")
        print("       定时/日志会偏 8 小时，建议：")
        print("       sudo timedatectl set-timezone Asia/Shanghai")
        return False
    print(f"  [OK] 机器时间 UTC{offset:+d}（{now_local.strftime('%Y-%m-%d %H:%M')}）")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查，不装也不建表")
    ap.add_argument("--install", action="store_true", help="（兼容旧写法，默认就是装）")
    ap.add_argument("--skip-tables", action="store_true", help="只处理依赖，不建表")
    args = ap.parse_args()

    print("=" * 56)
    print("  友利奈绪 · 环境初始化")
    print("=" * 56)

    dry = args.check
    ok_py = check_python()
    ok_deps = check_deps(install=not dry)
    check_optional()
    check_clock()

    if not (ok_py and ok_deps):
        print()
        print("阻塞项未解决，先别建表 / 启动。")
        return 1

    if args.skip_tables or dry:
        print("  [--] 跳过建表（" + ("--check" if dry else "--skip-tables") + "）")
        return 0

    print()
    print("建表：")
    ok_tables = init_tables()
    if not ok_tables:
        print()
        print("建表没完成，修完再跑一次。")
        return 1

    print()
    print("迁移旧数据：")
    migrate_data()

    print()
    print("补定时表结构：")
    ensure_cron_schema()

    print()
    print("导入内置场景：")
    seed_scenes()

    print()
    print("=" * 60)
    print("  环境就绪，直接启动：")
    print("      python3 run.py")
    print()
    print("  需要单独排查时（都可选，正常部署不用跑）：")
    print("      python3 scripts/preflight.py    # 13 项环境自检")
    print("      python3 scripts/init_db.py      # 只建表（加 --apply）")
    print("      python3 scripts/migrate_v17.py  # 只迁移（加 --apply）")
    print("      python3 scripts/migrate_v18.py  # v18.17 events→memories（加 --apply）")
    print("      python3 scripts/seed_scenes.py  # 只导入场景（加 --apply）")
    print("      python3 scripts/run_tests.py    # 全量测试（968 条）")
    print("=" * 60)
    return 0
    print("建表没完成，修完再跑一次。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
