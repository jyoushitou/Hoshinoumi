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

    # Python 自动注入的模块级名字（__file__ / __name__ 等），静态检查看不到赋值
    dunders = {
        "__file__", "__name__", "__doc__", "__package__", "__spec__",
        "__loader__", "__builtins__", "__path__", "__cached__",
    }

    def walk(table):
        for sym in table.get_symbols():
            name = sym.get_name()
            # 只看「在函数里当全局用、但模块层没定义」的名字
            # 注意：3.13 的参数也会 is_global()=True，所以本地变量/参数要排除
            if sym.is_local() or sym.is_parameter():
                continue
            if name in dunders:
                continue
            if sym.is_global() and not sym.is_assigned() and not sym.is_imported():
                if name not in module_names and not hasattr(builtins, name):
                    problems.append((filename, table.get_lineno(), name, table.get_name()))
        for child in table.get_children():
            walk(child)

    walk(st)
    problems += check_local_order(src, filename)
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


# ===================== 局部变量先用后赋值（v10.3） =====================
# 典型写法：模块级定义过同名变量，函数里又赋值，
# Python 会把它当局部变量，于是第一次读它时炸 UnboundLocalError。

import ast as _ast


def _visit(node, assigns, loads, globals_, nonlocals):
    """处理节点本身，再递归子节点（不进入嵌套作用域）"""
    if isinstance(node, _ast.Name):
        if isinstance(node.ctx, _ast.Load):
            loads.append((node.id, node.lineno))
        else:
            assigns.setdefault(node.id, node.lineno)
    elif isinstance(node, _ast.arg):
        assigns.setdefault(node.arg, getattr(node, "lineno", 0))
    elif isinstance(node, _ast.Global):
        globals_.update(node.names)
        return
    elif isinstance(node, _ast.Nonlocal):
        nonlocals.update(node.names)
        return
    elif isinstance(node, (_ast.For, _ast.AsyncFor)) and isinstance(node.target, _ast.Name):
        assigns.setdefault(node.target.id, node.target.lineno)
    elif isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef, _ast.Lambda)):
        return
    elif isinstance(node, (_ast.ListComp, _ast.SetComp, _ast.DictComp, _ast.GeneratorExp)):
        return

    for child in _ast.iter_child_nodes(node):
        _visit(child, assigns, loads, globals_, nonlocals)


def check_local_order(src, filename="<src>"):
    """找出「函数内先用后赋值」的局部变量"""
    problems = []
    try:
        tree = _ast.parse(src)
    except SyntaxError:
        return problems

    for node in _ast.walk(tree):
        if not isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            continue
        assigns, loads = {}, []
        globals_, nonlocals = set(), set()

        for a in list(node.args.args) + list(node.args.kwonlyargs) + list(node.args.posonlyargs):
            assigns.setdefault(a.arg, node.lineno)
        if node.args.vararg:
            assigns.setdefault(node.args.vararg.arg, node.lineno)
        if node.args.kwarg:
            assigns.setdefault(node.args.kwarg.arg, node.lineno)

        for stmt in node.body:
            _visit(stmt, assigns, loads, globals_, nonlocals)

        for name, line in loads:
            if name in globals_ or name in nonlocals:
                continue
            first_assign = assigns.get(name)
            if first_assign is not None and line < first_assign:
                problems.append((filename, line, name,
                                 f"{node.name} 里先用后赋值（首次赋值在第 {first_assign} 行）"))
    return problems


if __name__ == "__main__":
    sys.exit(main())
