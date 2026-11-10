#!/usr/bin/env python3
# ===================== 分发前检查 =====================
# 打包给别人之前跑一遍：查有没有把密码、密钥、私人信息打进包里。
#
#     python3 scripts/check_dist.py              # 查源码
#     python3 scripts/check_dist.py --zip dist/nao-16.0.0-src.zip
#
# 退出码：0 = 没发现严重问题；1 = 有必须处理的

import argparse
import os
import re
import sys
import zipfile

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (级别, 说明, 正则)
RULES = [
    ("HIGH", "数据库密码默认值写死在代码里",
     re.compile(r'_os\.getenv\("NAO_DB_PASS",\s*"([^"]*)"\)')),
    ("MID", "主人 QQ 号写死（可以考虑改成环境变量）",
     re.compile(r"MASTER_QQ\s*=\s*int\(_os\.getenv\(\"NAO_MASTER_QQ\",\s*\"(\d{6,12})\"\)\)")),
    ("MID", "内网数据库地址",
     re.compile(r'"host"\s*:\s*_os\.getenv\("NAO_DB_HOST",\s*"(\d+\.\d+\.\d+\.\d+)"\)')),
    ("LOW", "内网 IP",
     re.compile(r"\b(192\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
]

SAFE_VALUES = {"CHANGE_ME", "", "YOUR_PASSWORD"}

SKIP_DIRS = {".git", ".venv", "venv", "dist", "data", "__pycache__", ".tmp", "node_modules", "vendor"}
SKIP_EXT = (".pyc", ".zip", ".bundle", ".log", ".png", ".jpg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".otf")


def scan_text(text, filename):
    hits = []
    for level, desc, pattern in RULES:
        for m in pattern.finditer(text):
            value = m.group(m.lastindex) if m.lastindex else ""
            if level == "HIGH" and value in SAFE_VALUES:
                continue
            line_no = text[:m.start()].count("\n") + 1
            hits.append((level, desc, filename, line_no, value))
    return hits


def scan_repo():
    hits = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(SKIP_EXT):
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT)
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            hits += scan_text(text, rel)
    return hits


def scan_zip(path):
    hits = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.filename.endswith(SKIP_EXT):
                continue
            try:
                text = z.read(info).decode("utf-8", "ignore")
            except Exception:
                continue
            hits += scan_text(text, info.filename)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", help="检查已打好的 zip")
    args = ap.parse_args()

    print("=" * 56)
    print("  分发前检查")
    print("=" * 56)

    hits = scan_zip(args.zip) if args.zip else scan_repo()
    target = args.zip or "源码目录"
    print(f"  目标：{target}\n")

    if not hits:
        print("  [OK] 没发现敏感信息")
        return 0

    order = {"HIGH": 0, "MID": 1, "LOW": 2}
    hits.sort(key=lambda h: order.get(h[0], 9))
    for level, desc, filename, line_no, value in hits:
        shown = (value[:4] + "*" * max(0, len(value) - 4)) if value else ""
        print(f"  [{level}] {desc}")
        print(f"         {filename}:{line_no}  {shown}")

    high = sum(1 for h in hits if h[0] == "HIGH")
    mid = sum(1 for h in hits if h[0] == "MID")
    low = sum(1 for h in hits if h[0] == "LOW")
    print(f"\n  合计：HIGH {high} / MID {mid} / LOW {low}")
    if high:
        print("\n  [X] 有 HIGH 级问题，分发前必须处理（改成环境变量或空默认值）")
        return 1
    print("\n  [!] 只有中低风险，确认可接受后再分发")
    return 0


if __name__ == "__main__":
    sys.exit(main())
