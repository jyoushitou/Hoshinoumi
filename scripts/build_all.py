#!/usr/bin/env python3
# ===================== 一键打包全套 =====================
# 在开发机上跑这一条，把所有能做的包都做出来：
#
#     python3 scripts/build_all.py                    # 版本号自动取
#     python3 scripts/build_all.py --version 16.0.0
#     python3 scripts/build_all.py --with-browser     # Docker 里带 Chromium
#     python3 scripts/build_all.py --skip docker      # 跳过某一项
#
# 产出（能做的都做，做不了的会写清原因，不会中断）：
#     release/nao-<ver>-src.zip        源码包
#     release/nao-<ver>-full.zip       整包（含依赖，需要 vendor/ 或 pip 能装）
#     release/nao-<ver>[.exe]          单文件可执行（需要 pyinstaller）
#     nao-bot:<ver>                 Docker 镜像（需要 docker 守护进程）
#     release/nao-<ver>.bundle         git 包（给仓库同步用）

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "release")   # v17.x：产物集中放这里
PY = sys.executable
IS_WIN = platform.system() == "Windows"


def run(cmd, cwd=None, quiet=False):
    """跑子进程；返回 (退出码, 合并输出)"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run(cmd, cwd=cwd or ROOT, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True,
                          encoding="utf-8", errors="ignore")
    out = (proc.stdout or "").strip()
    if not quiet:
        for line in out.splitlines()[-6:]:
            print("   " + line)
    return proc.returncode, out


def has_module(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def auto_version():
    rc, out = run(["git", "describe", "--tags", "--abbrev=0"], quiet=True)
    if rc == 0 and out:
        return out.lstrip("v")
    rc, out = run(["git", "rev-parse", "--short", "HEAD"], quiet=True)
    return f"0.0.0-dev-{out}" if rc == 0 else "0.0.0-dev"


def step_source(version):
    print("\n>> [1/5] 源码包")
    rc, _ = run([PY, os.path.join("scripts", "package.py"), "--version", f"v{version}"])
    path = os.path.join(DIST, f"nao-{version}-src.zip")
    return (rc == 0 and os.path.exists(path)), path, "" if rc == 0 else "脚本报错"


def step_full(version):
    print("\n>> [2/5] 整包（含依赖）")
    vendor = os.path.join(ROOT, "vendor")
    if not os.path.isdir(vendor):
        print("   没有 vendor/，先尝试装一份…")
        rc, _ = run([PY, "-m", "pip", "install", "--target", "vendor",
                     "-r", "requirements.txt", "--no-cache-dir",
                     "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"], quiet=True)
        if rc != 0:
            print("   [SKIP] 跳过：pip 装不进 vendor/（网络或权限问题）")
            print("      手动解决：pip install --target vendor -r requirements.txt")
            return False, "", "pip 不可用"

    rc, _ = run([PY, os.path.join("scripts", "package.py"),
                 "--version", f"v{version}", "--deps"])
    path = os.path.join(DIST, f"nao-{version}-full.zip")
    return (rc == 0 and os.path.exists(path)), path, "" if rc == 0 else "打包失败"


def step_exe(version):
    print(f"\n>> [3/5] 单文件可执行（当前平台：{platform.system()}）")
    if not has_module("PyInstaller"):
        print("   [SKIP] 跳过：没装 pyinstaller")
        print(f"      装：{('py -m pip' if IS_WIN else 'python3 -m pip')} install pyinstaller")
        return False, "", "没装 pyinstaller"

    rc, _ = run([PY, os.path.join("scripts", "build_exe.py"), "--version", version])
    name = f"nao-{version}.exe" if IS_WIN else f"nao-{version}"
    path = os.path.join(DIST, name)
    return (rc == 0 and os.path.exists(path)), path, "" if rc == 0 else "构建失败"


def step_docker(version, with_browser):
    print("\n>> [4/5] Docker 镜像")
    if shutil.which("docker") is None:
        print("   [SKIP] 跳过：没装 docker")
        return False, "", "没装 docker"
    if subprocess.call(["docker", "info"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL) != 0:
        print("   [SKIP] 跳过：docker 守护进程没运行")
        print("      Linux: sudo systemctl start docker / Windows: 打开 Docker Desktop")
        return False, "", "docker 守护进程未运行"

    cmd = [PY, os.path.join("scripts", "build_docker.py"), "--version", version, "--save"]
    if with_browser:
        cmd.append("--browser")
    rc, _ = run(cmd)
    tag = f"nao-bot:{version}" + ("-browser" if with_browser else "")
    suf = "-browser" if with_browser else ""
    path = os.path.join(DIST, f"nao-bot-{version}{suf}.tar.gz")
    return (rc == 0), path if os.path.exists(path) else tag, "" if rc == 0 else "构建失败"


def step_bundle(version):
    print("\n>> [5/5] git bundle（仓库同步用）")
    rc, out = run(["git", "status", "--porcelain"], quiet=True)
    if out:
        print("   [!] 工作区有未提交改动，bundle 只包含已提交内容")
    path = os.path.join(DIST, f"nao-{version}.bundle")
    rc, _ = run(["git", "bundle", "create", path, "main", "--tags"])
    return (rc == 0 and os.path.exists(path)), path, "" if rc == 0 else "git bundle 失败"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", help="形如 16.0.0（默认取最近 tag）")
    ap.add_argument("--with-browser", action="store_true", help="Docker 镜像里带 Chromium")
    ap.add_argument("--skip", default="", help="跳过：src,full,exe,docker,bundle（逗号分隔）")
    args = ap.parse_args()

    version = (args.version or auto_version()).strip().lstrip("v")
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    print("=" * 60)
    print(f"  一键打包 {version}   （{platform.system()} {platform.machine()}）")
    print("=" * 60)

    started = time.time()
    results = []

    def record(name, fn):
        try:
            ok, path, why = fn()
        except Exception as e:
            ok, path, why = False, "", f"异常：{e}"
        results.append((name, ok, path, why))

    if "src" not in skip:
        record("源码包", lambda: step_source(version))
    if "full" not in skip:
        record("整包", lambda: step_full(version))
    if "exe" not in skip:
        record("单文件", lambda: step_exe(version))
    if "docker" not in skip:
        record("Docker", lambda: step_docker(version, args.with_browser))
    if "bundle" not in skip:
        record("git bundle", lambda: step_bundle(version))

    print("\n" + "=" * 60)
    print("  结果")
    print("=" * 60)
    ok_count = 0
    for name, ok, path, why in results:
        mark = "[OK]" if ok else "[SKIP]"
        ok_count += 1 if ok else 0
        shown = os.path.relpath(path, ROOT) if path and os.path.exists(str(path)) else (path or "-")
        print(f"  {mark} {name:10} {shown}")
        if not ok and why:
            print(f"       原因：{why}")
    print(f"\n  成功 {ok_count}/{len(results)}，用时 {time.time() - started:.0f} 秒")
    print(f"  产物目录：{os.path.relpath(DIST, ROOT)}/")
    return 0 if ok_count else 1


if __name__ == "__main__":
    sys.exit(main())
