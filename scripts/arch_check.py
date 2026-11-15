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


def import_cycles():
    """只看模块顶层的 import，检测真实 import 环（函数内懒加载不算）。"""
    import ast
    from pathlib import Path as _P

    files = {}
    for p in BOT.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(BOT).with_suffix("")
        mod = "bot." + ".".join(rel.parts)
        if mod.endswith(".__init__"):
            mod = mod[:-9]
        files[mod] = p

    def resolve(base, level, mod):
        if level == 0:
            return mod or ""
        parts = base.split(".")
        # base 是包名（__init__ 所在模块）；level=1 当前包，level=2 上一级
        keep = parts[:len(parts) - level + 1]
        if mod:
            keep += mod.split(".")
        return ".".join(keep)

    graph = {}
    for mod, path in files.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        deps = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.startswith("bot."):
                        deps.add(a.name)
            elif isinstance(node, ast.ImportFrom):
                base = mod
                target = resolve(base, node.level or 0, node.module or "")
                if target.startswith("bot."):
                    deps.add(target)
                    for a in node.names:
                        if a.name != "*":
                            deps.add(target + "." + a.name)
        graph[mod] = {d for d in deps if d in files and d != mod}

    color = {}
    stack = []
    cycles = []

    def dfs(u):
        color[u] = 1
        stack.append(u)
        for v in graph.get(u, ()):
            if color.get(v, 0) == 0:
                dfs(v)
            elif color.get(v) == 1:
                i = stack.index(v)
                cyc = stack[i:] + [v]
                key = tuple(sorted(set(cyc)))
                if key not in [tuple(sorted(set(c))) for c in cycles]:
                    cycles.append(cyc)
        stack.pop()
        color[u] = 2

    for m in sorted(graph):
        if color.get(m, 0) == 0:
            dfs(m)
    return cycles


def check(limit=100):
    return {
        "long_functions": long_functions(limit),
        "events_reads": events_reads(),
        "startup_ddl": startup_ddl(),
        "persistence_cycle": log_cycle(),
        "import_cycles": import_cycles(),
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
