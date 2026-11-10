#!/usr/bin/env python3
# ===================== 程序打包 =====================
# 产出「能直接跑的 Python 程序包」，跟 .bundle（git 运输用）是两回事。
#
#     python3 scripts/package.py --version v16.0.0            # 源码包（A）
#     python3 scripts/package.py --version v16.0.0 --deps     # 带依赖整包（B）
#     python3 scripts/package.py --version v16.0.0 --deps --site-packages
#
# 产物在 dist/：
#     nao-16.0.0-src.zip      源码包：解压 → pip install -r requirements → python3 run.py
#     nao-16.0.0-full.zip     整包：解压 → ./start.sh（依赖已内置）

import argparse
import os
import shutil
import sys
import zipfile
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

# 不进包的东西
EXCLUDE_DIRS = {
    ".git", ".venv", "venv", ".vendor", "vendor", ".tmp", "dist", "data",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    ".playwright-browsers", "node_modules",
}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".bundle", ".log", ".pid", ".zip")
EXCLUDE_FILES = {".DS_Store", "Thumbs.db", ".nao-ref-glyphs.json"}

# 整包要带上的运行目录
RUNTIME_DIRS = ("botv", "personas", "scripts", "docs")
RUNTIME_FILES = ("run.py", "README.md", "requirements.txt", "botsetting.yaml")

START_SH = """#!/usr/bin/env bash
# 由 scripts/package.py 生成：用内置依赖启动
set -e
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/vendor:${PYTHONPATH:-}"
export PYTHONIOENCODING=utf-8
exec python3 run.py "$@"
"""


def iter_files(include_deps=False):
    """遍历要打进包的文件（相对路径）"""
    for base, dirs, files in os.walk(ROOT):
        rel_base = os.path.relpath(base, ROOT)
        if rel_base == ".":
            rel_base = ""
        parts = [p for p in rel_base.split(os.sep) if p]
        if parts and parts[0] in EXCLUDE_DIRS:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for name in files:
            rel = os.path.join(rel_base, name) if rel_base else name
            if name in EXCLUDE_FILES or name.endswith(EXCLUDE_SUFFIX):
                continue
            yield rel


def build_zip(zip_path, files, extra=None):
    os.makedirs(DIST, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            path = os.path.join(ROOT, rel)
            try:
                z.write(path, rel)
                count += 1
            except Exception as e:
                print(f"   跳过 {rel}: {e}")
        for rel, content in (extra or {}).items():
            z.writestr(rel, content)
            count += 1
    size = os.path.getsize(zip_path) / 1024
    print(f"   ✅ {os.path.relpath(zip_path, ROOT)}（{count} 个文件，{size:.0f} KB）")
    return count


def find_site_packages():
    """找当前解释器的 site-packages（用于整包）"""
    for p in sys.path:
        if p and p.endswith("site-packages") and os.path.isdir(p):
            return p
    return None


def copy_vendor(site_packages, staging):
    """把依赖复制进 vendor/"""
    skip = {"pip", "setuptools", "wheel", "pkg_resources", "_distutils_hack", "distutils-precedence.pth"}
    os.makedirs(staging, exist_ok=True)
    copied = 0
    for name in os.listdir(site_packages):
        if name.split(".")[0] in skip or name in skip:
            continue
        src = os.path.join(site_packages, name)
        dst = os.path.join(staging, name)
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            copied += 1
        except Exception as e:
            print(f"   跳过 {name}: {e}")
    return copied


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="形如 v16.0.0")
    ap.add_argument("--deps", action="store_true", help="同时打整包（含依赖）")
    ap.add_argument("--site-packages", action="store_true",
                    help="整包依赖从 site-packages 复制（默认用 vendor/ 目录）")
    args = ap.parse_args()

    version = args.version.strip().lstrip("v")
    print("=" * 56)
    print(f"  打包 {version}")
    print("=" * 56)

    os.makedirs(DIST, exist_ok=True)
    files = list(iter_files())
    print(f"\n▶ 源码包（{len(files)} 个文件）")
    src_zip = os.path.join(DIST, f"nao-{version}-src.zip")
    build_zip(src_zip, files, extra={
        "启动说明.txt": (
            f"友利奈绪 QQ 机器人 {version}（源码包）\n\n"
            "1. 安装依赖：pip install -r requirements.txt\n"
            "2. 确认 MySQL 可用，并先跑过 scripts/migrate_v7.py / migrate_v8.py\n"
            "3. 启动：python3 run.py\n\n"
            "自检：python3 scripts/preflight.py\n"
            f"打包时间：{datetime.now():%Y-%m-%d %H:%M}\n"
        )
    })

    if not args.deps:
        print("\n完成。要带依赖的整包，加 --deps")
        return 0

    print("\n▶ 整包（含依赖）")
    staging = os.path.join(ROOT, ".tmp-vendor")
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging, exist_ok=True)

    if args.site_packages:
        sp = find_site_packages()
        print(f"   从 site-packages 复制：{sp}")
        if not sp:
            print("   ❌ 找不到 site-packages")
            return 1
        n = copy_vendor(sp, staging)
    else:
        vendor = os.path.join(ROOT, "vendor")
        if not os.path.isdir(vendor):
            print("   ❌ 没有 vendor/ 目录")
            print("      先建：pip install --target vendor -r requirements.txt")
            return 1
        shutil.copytree(vendor, staging, dirs_exist_ok=True)
        n = len(os.listdir(vendor))
    print(f"   已收集 {n} 个依赖")

    full_files = list(files)
    for base, dirs, fnames in os.walk(staging):
        for name in fnames:
            rel = os.path.relpath(os.path.join(base, name), staging)
            full_files.append(os.path.join("vendor", rel))

    full_zip = os.path.join(DIST, f"nao-{version}-full.zip")
    build_zip(full_zip, full_files, extra={
        "start.sh": START_SH,
        "启动说明.txt": (
            f"友利奈绪 QQ 机器人 {version}（整包，依赖已内置）\n\n"
            "1. 解压\n"
            "2. chmod +x start.sh\n"
            "3. ./start.sh\n\n"
            "依赖在 vendor/ 里，不需要联网装包。\n"
            f"打包时间：{datetime.now():%Y-%m-%d %H:%M}\n"
        ),
    })
    shutil.rmtree(staging, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
