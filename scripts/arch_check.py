#!/usr/bin/env python3
"""v21.9 架构闸门：0 个 >100 行函数、无 startup DDL、无 events 读路径。

    python3 scripts/arch_check.py --strict
"""

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOT = ROOT / "bot"


def long_functions(limit=100):
    bad = []
    for p in BOT.rglob("*.py"):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                line = getattr(n, "end_lineno", n.lineno) - n.lineno + 1
                if line > limit:
                    bad.append((str(p.relative_to(ROOT)), n.name, line))
    return bad


def events_reads():
    bad = []
    for p in BOT.rglob("*.py"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "FROM events" in text or "JOIN events" in text:
            bad.append(str(p.relative_to(ROOT)))
    return bad


def startup_ddl():
    p = ROOT / "bot" / "app" / "bootstrap.py"
    text = p.read_text(encoding="utf-8")
    return [x for x in ("CREATE TABLE", "ALTER TABLE", "DROP TABLE") if x in text]


def log_cycle():
    settings = (ROOT / "bot" / "core" / "settings.py").read_text(encoding="utf-8")
    log = (ROOT / "bot" / "log.py").read_text(encoding="utf-8")
    bad = []
    if "from ..log" in settings or "import log_api" in settings:
        bad.append("settings -> log")
    if "get_cursor" in log or "from .infra import conn" in log:
        bad.append("log -> db")
    return bad


def check(limit=100):
    return {
        "long_functions": long_functions(limit),
        "events_reads": events_reads(),
        "startup_ddl": startup_ddl(),
        "persistence_cycle": log_cycle(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--max-lines", type=int, default=100)
    args = ap.parse_args()
    result = check(args.max_lines)
    failed = {k: v for k, v in result.items() if v}
    for k, v in result.items():
        print(f"{'[X]' if v else '[OK]'} {k}: {v if v else 'clean'}")
    if failed and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
