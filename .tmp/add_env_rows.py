import sys

path = "docs/发布检查清单.md"
lines = open(path, encoding="utf-8").read().splitlines()
BT = chr(96)
rows = [
    ("NAO_MASTER_QQ", "822891053", "主人 QQ（决定谁能用命令）", "core/constants.py"),
    ("NAO_LISTEN_HOST", "0.0.0.0", "WebSocket 监听地址", "core/constants.py"),
    ("NAO_WS_PORT", "3001", "NapCat 连进来的端口", "core/constants.py"),
    ("NAO_API_PORT", "60908", "HTTP API 端口", "core/constants.py"),
    ("NAO_DB_HOST", "192.168.0.50", "数据库地址", "core/constants.py"),
    ("NAO_DB_PORT", "3306", "数据库端口", "core/constants.py"),
    ("NAO_DB_USER", "TomoriNaoBot", "数据库用户", "core/constants.py"),
    ("NAO_DB_PASS", "TNB", "数据库密码", "core/constants.py"),
    ("NAO_DB_NAME", "TomoriNaoBotData", "数据库名", "core/constants.py"),
]

idx = None
for i, ln in enumerate(lines):
    if "NAO_BOOK_URLS" in ln:
        idx = i
if idx is None:
    print("找不到锚点")
    sys.exit(1)

existing = "\n".join(lines)
added = [
    f"| {BT}{n}{BT} | {d} | {desc} | {BT}{p}{BT} |"
    for n, d, desc, p in rows
    if f"{BT}{n}{BT}" not in existing
]
lines[idx + 1: idx + 1] = added
open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("已插入", len(added), "行")
