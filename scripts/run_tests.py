#!/usr/bin/env python3
# ===================== 一键跑测试 =====================
#     python3 scripts/run_tests.py            # tests + checks 全跑
#     python3 scripts/run_tests.py --fast     # 只跑 tests（跳过 checks）
#     python3 scripts/run_tests.py checks     # 只跑某一个
#
# tests   ：功能测试（分模块 + 冒烟）
# checks  ：前置环境监测 + 迁移检查

import argparse
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITES = {
    "tests": "功能测试（分模块 + 冒烟）",
    "checks": "前置环境 + 迁移",
}


def run_suite(name):
    path = os.path.join(ROOT, name)
    if not os.path.isdir(path):
        print(f"  [跳过] {name}/ 不存在")
        return 0, 0, False

    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", name],
        cwd=ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="ignore",
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    ran = 0
    for line in out.splitlines():
        if line.startswith("Ran "):
            try:
                ran = int(line.split()[1])
            except Exception:
                pass
    ok = "OK" in out and proc.returncode == 0
    mark = "[OK]" if ok else "[X]"
    print(f"  {mark} {name:8} {SUITES.get(name, '')} —— {ran} 条")
    if not ok:
        tail = [ln for ln in out.splitlines() if ln.startswith(("FAIL:", "ERROR:", "AssertionError"))]
        for ln in tail[:10]:
            print("       " + ln)
    return ran, 0 if ok else 1, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", nargs="?", help="tests / checks；不传就跑全部")
    ap.add_argument("--fast", action="store_true", help="只跑 tests")
    args = ap.parse_args()

    if args.suite:
        targets = [args.suite]
    elif args.fast:
        targets = ["tests"]
    else:
        targets = list(SUITES)

    print("=" * 56)
    print("  跑测试")
    print("=" * 56)

    total, failed = 0, 0
    for name in targets:
        ran, rc, _ok = run_suite(name)
        total += ran
        failed += rc

    print("-" * 56)
    print(f"  合计 {total} 条，失败 {failed} 个套件")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
