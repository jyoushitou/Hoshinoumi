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
#     setup.py → preflight.py → run.py

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
        from botv.infra import schema
        from botv.infra.conn import get_cursor
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

    print()
    if ok_tables:
        print("环境就绪。下一步：")
        print("    python3 scripts/preflight.py     # 完整自检（可选）")
        print("    python3 run.py                   # 启动")
        return 0
    print("建表没完成，修完再跑一次。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
