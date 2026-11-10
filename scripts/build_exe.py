#!/usr/bin/env python3
# ===================== 单文件可执行包 =====================
# 用 PyInstaller 把整个程序打成一个 ELF（Linux）/ exe（Windows）。
#
#     python3 scripts/build_exe.py --version 16.0.0
#
# 注意：**不能跨平台交叉编译**——要 Linux 版就得在 Linux 上跑这个脚本。
#
# 目标机效果：
#     ./nao-16.0.0            # 直接启动，不用装 python、不用装依赖
#
# 代价：
#     - 体积 ~60 MB（Python 解释器 + 依赖都打进去了）
#     - 每次改代码都要重新构建
#     - personas/ 是外置数据，会一起打进去；想换角色卡还是要改外面那份

import argparse
import os
import platform
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

# 这些包 PyInstaller 有时找不到，显式声明
HIDDEN_IMPORTS = [
    "websockets", "websockets.legacy", "websockets.legacy.server",
    "aiohttp", "aiohttp.web", "pymysql", "pymysql.cursors",
    "jieba", "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
    "requests", "urllib3", "json", "sqlite3",
]


def sep():
    return ";" if platform.system() == "Windows" else ":"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="形如 16.0.0")
    ap.add_argument("--console", action="store_true", default=True,
                    help="保留控制台（机器人需要看日志，默认开）")
    args = ap.parse_args()

    version = args.version.strip().lstrip("v")

    print("=" * 56)
    print(f"  构建可执行文件 {version}")
    print("=" * 56)
    print(f"  平台：{platform.system()} {platform.machine()}")

    try:
        import PyInstaller  # noqa: F401
    except Exception:
        print("\n❌ 没有 pyinstaller")
        print("   先装：python3 -m pip install --user --break-system-packages pyinstaller")
        return 1

    os.makedirs(DIST, exist_ok=True)
    name = f"nao-{version}"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", name,
        "--distpath", DIST,
        "--workpath", os.path.join(ROOT, ".tmp", "pyinstaller-build"),
        "--specpath", os.path.join(ROOT, ".tmp"),
        "--console" if args.console else "--windowed",
        # 角色卡是外部数据，必须一起打进去
        "--add-data", f"personas{sep()}personas",
        "--add-data", f"docs{sep()}docs",
        "--collect-submodules", "websockets",
    ]
    for mod in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", mod]

    cmd.append(os.path.join(ROOT, "run.py"))

    print("\n▶ 开始构建（第一次会慢，2~5 分钟）")
    print("   " + " ".join(cmd[:6]) + " ...")
    rc = subprocess.call(cmd, cwd=ROOT)
    if rc != 0:
        print(f"\n❌ 构建失败（退出码 {rc}）")
        return rc

    out = os.path.join(DIST, name + (".exe" if platform.system() == "Windows" else ""))
    if os.path.exists(out):
        size = os.path.getsize(out) / 1024 / 1024
        print(f"\n✅ {os.path.relpath(out, ROOT)}（{size:.0f} MB）")
        print("   目标机直接运行即可，不需要 python 和依赖。")
        print("   注意：personas/ 已打进去，但改角色卡需要重新构建。")
    else:
        print("\n⚠️ 没找到产物，检查 PyInstaller 输出")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
