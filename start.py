#!/usr/bin/env python3
"""Hoshinoumi（REC）一键启动（v19.5.7）

顺序：
  1. 数据库迁移（升级时第一步；幂等）
  2. 检查 API 密钥；缺失则询问是否启动配置向导
  3. 环境监测（API/依赖/数据库/表结构/视觉）
  4. run.py
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def _run(script, *args):
    print(f"\n▶ {Path(script).name} {' '.join(args)}".rstrip())
    return subprocess.run([PY, str(ROOT / script), *args]).returncode


def _api_missing():
    try:
        from botv.infra import repo_key
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


def main():
    if "--no-migrate" not in sys.argv:
        rc = _run("scripts/migrate.py", "--apply")
        if rc != 0:
            print("❌ 迁移失败，停止启动。")
            return rc

    missing = _api_missing()
    if missing and _ask_config(missing) != 0:
        return 1

    rc = _run("checks/env_check.py")
    if rc != 0:
        print("\n❌ 环境监测未通过，按上面的提示修复后重跑：python3 start.py")
        return rc

    print("\n▶ 启动 run.py\n")
    os.execv(PY, [PY, str(ROOT / "run.py")])


if __name__ == "__main__":
    raise SystemExit(main())
