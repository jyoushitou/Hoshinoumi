#!/usr/bin/env python3
# ===================== worker 版本清理命令（v25.5.8） =====================
# ingress 内部也会自动执行同一套清理；这个脚本用于手动检查/清理。

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.core.worker_gc import select_removable  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(ROOT / "data" / "workers"))
    ap.add_argument("--keep", type=int, default=2, help="保留 current + keep 个版本")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    base = Path(args.base).resolve()
    out = select_removable(base, max(1, args.keep))
    if not out:
        print("[gc] 没有可清理版本")
        return 0
    for p in out:
        print(f"[gc] {'删除' if args.apply else '可删除'} {p}")
        if args.apply:
            __import__("shutil").rmtree(p, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
