#!/usr/bin/env python3
# ===================== 未定义名字检查 =====================
# 用 symtable 扫「引用了、但既没导入也没定义」的全局名。
#
# 为什么需要它：批量改代码时，import 可能没落地（例如锚点字符串没匹配上），
# 于是某个名字在函数里被引用却不存在——只有运行到那行才炸，测试未必覆盖。
#
# 用法：
#     python3 scripts/check_names.py            # 扫 botv/ 和 run.py
#     python3 scripts/check_names.py 路径 ...

import builtins
import os
import sys
import symtable

SKIP_DIRS = {"__pycache__", ".git", ".venv", "images", "sticker_archive"}


def check_source(src, filename):
    """返回 [(文件名, 行号, 名字, 作用域)]"""
    problems = []
    try:
        st = symtable.symtable(src, filename, "exec")
    except SyntaxError as e:
        return [(filename, e.lineno or 0, "<语法错误>", str(e))]

    module_names = set(st.get_identifiers())

    def walk(table):
        for sym in table.get_symbols():
            name = sym.get_name()
            # 只看「在函数里当全局用、但模块层没定义」的名字
            if sym.is_global() and not sym.is_assigned() and not sym.is_imported():
                if name not in module_names and not hasattr(builtins, name):
                    problems.append((filename, table.get_lineno(), name, table.get_name()))
        for child in table.get_children():
            walk(child)

    walk(st)
    return problems


def scan(paths):
    problems = []
    for path in paths:
        if os.path.isfile(path) and path.endswith(".py"):
            with open(path, encoding="utf-8") as f:
                problems += check_source(f.read(), path)
            continue
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                if not name.endswith(".py"):
                    continue
                full = os.path.join(root, name)
                try:
                    with open(full, encoding="utf-8") as f:
                        problems += check_source(f.read(), full)
                except Exception as e:
                    problems.append((full, 0, "<读不了>", str(e)))
    return problems


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    targets = sys.argv[1:] or [os.path.join(root, "botv"), os.path.join(root, "run.py")]
    problems = scan(targets)
    if not problems:
        print("✅ 没有发现未定义的名字")
        return 0
    print(f"❌ 发现 {len(problems)} 处未定义的名字：")
    for path, line, name, scope in problems:
        rel = os.path.relpath(path, root)
        print(f"   {rel}:{line}  {name}  （在 {scope} 里）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
