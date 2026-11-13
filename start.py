#!/usr/bin/env python3
"""Hoshinoumi（REC）一键启动（v20）

启动顺序：
  1. 数据库迁移（有迁移脚本时执行；幂等）
  2. 第一次启动 / API Key 缺失时，运行 API 配置向导
  3. 环境检查（checks/env_check.py）
  4. 需要对外服务时启动 C++ 网关（可选）
  5. run.py

网关开关：
  python3 start.py --gateway      强制启动
  python3 start.py --no-gateway   强制不启动
  NAO_GATEWAY=1 python3 start.py  环境变量启动
  交互终端下会询问；非交互默认不启动
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def _run(script, *args):
    print(f"\n▶ {Path(script).name} {' '.join(args)}".rstrip())
    return subprocess.run([PY, str(ROOT / script), *args]).returncode


def _api_missing():
    try:
        from bot.infra import repo_key
        names = ("DS_API_KEY", "ARK_API_KEY")  # ALAPI 可选
        return [n for n in names if not (repo_key.get_api_key_from_db(n)
                                         or os.getenv(n, ""))]
    except Exception:
        return ["数据库未就绪"]


def _ask_config(missing):
    print("\n⚠️ API 未配置：" + "、".join(missing))
    print("可以现在运行交互配置向导，直接填 Key，不用手写 SQL。")
    if not sys.stdin.isatty():
        print("非交互环境，跳过；请先运行：python3 scripts/configure_api.py")
        return 1
    try:
        ans = input("是否现在运行配置向导？[Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return 1
    if ans in ("", "y", "yes"):
        return _run("scripts/configure_api.py")
    print("已跳过；可稍后运行：python3 scripts/configure_api.py")
    return 0


def _want_gateway():
    """是否启动网关：命令行 > 环境变量 > 交互询问；非交互默认否"""
    args = set(sys.argv[1:])
    if "--no-gateway" in args:
        return False
    if "--gateway" in args:
        return True
    env = os.getenv("NAO_GATEWAY", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    if sys.stdin.isatty():
        try:
            ans = input("\n是否启动网关（对外服务）？[y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return ans in ("y", "yes")
    return False


def _find_gateway():
    for name in ("rec_gateway", "rec_gateway.exe"):
        p = ROOT / "gateway" / "build" / name
        if p.exists():
            return p
    return None


def _start_gateway():
    """启动网关；返回 Popen，失败返回 None"""
    binary = _find_gateway()
    if binary is None:
        print("❌ 找不到网关二进制：gateway/build/rec_gateway（或 .exe）")
        print("   先构建：见 gateway/README.md；或用发布版 Docker 镜像。")
        return None
    cfg = ROOT / "config" / "gateway.json"
    if not cfg.exists():
        print(f"❌ 找不到网关配置：{cfg}")
        print("   先运行：python3 scripts/configure.py")
        return None

    print(f"\n▶ 启动网关：{binary} --config {cfg}")
    proc = subprocess.Popen([str(binary), "--config", str(cfg)], cwd=str(ROOT))
    time.sleep(1.0)
    if proc.poll() is not None:
        print(f"❌ 网关启动失败（退出码 {proc.returncode}）")
        return None
    print(f"✅ 网关已启动（PID {proc.pid}）")
    return proc


def _stop_gateway(proc):
    if proc is None or proc.poll() is not None:
        return
    print("\n▶ 停止网关")
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main():
    # 1. 数据库迁移（有脚本才跑）
    if "--no-migrate" not in sys.argv and (ROOT / "scripts/migrate.py").exists():
        rc = _run("scripts/migrate.py", "--apply")
        if rc != 0:
            print("❌ 迁移失败，停止启动。")
            return rc

    # 2. 第一次启动 / API 缺失时配置
    missing = _api_missing()
    if missing and _ask_config(missing) != 0:
        return 1

    # 3. 环境检查
    rc = _run("checks/env_check.py")
    if rc != 0:
        print("\n❌ 环境监测未通过，按上面的提示修复后重跑：python3 start.py")
        return rc

    # 4. 可选网关（必须在 run.py 之前）
    gateway = None
    if _want_gateway():
        gateway = _start_gateway()
        if gateway is None:
            return 1

    # 5. bot 主程序；退出时回收网关
    try:
        print("\n▶ 启动 run.py\n")
        return subprocess.run([PY, str(ROOT / "run.py")], cwd=str(ROOT)).returncode
    except KeyboardInterrupt:
        print("\n[已中断] 收到 Ctrl-C，程序退出。")
        return 130
    finally:
        _stop_gateway(gateway)


if __name__ == "__main__":
    raise SystemExit(main())
