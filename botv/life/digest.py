# ===================== 会话浓缩（v14.1-D3） =====================
# 每聊 10 轮，把这段压成「一行」，攒成她自己的记录文档。
#
# 原则：**极简**。一行不超过 40 字，只留事实，不留评价。
# 文档只保留最近 20 行——旧的会被挤掉，不会无限增长。

import os
import re
from datetime import datetime

from ..config import CST
from ..log import log_api

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIGEST_DIR = os.path.join(ROOT, "data", "digests")
MAX_LINES = 20
MAX_LINE_CHARS = 40
ROUNDS_PER_DIGEST = 10  # 每攒够 10 轮溢出对话就浓缩一行


def _path(tid):
    os.makedirs(DIGEST_DIR, exist_ok=True)
    safe = re.sub(r"[^0-9A-Za-z_-]", "_", str(tid))
    return os.path.join(DIGEST_DIR, f"{safe}.md")


def load(tid):
    """读这个对象的浓缩文档"""
    try:
        with open(_path(tid), encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _trim_lines(lines):
    lines = [ln for ln in lines if ln.strip()]
    return lines[-MAX_LINES:]


def append(tid, line):
    """追加一行；太长就截断，超量就丢最旧的"""
    line = (line or "").strip().replace("\n", " ")
    if not line:
        return False
    if len(line) > MAX_LINE_CHARS:
        line = line[:MAX_LINE_CHARS - 1] + "…"
    stamp = datetime.now(CST).strftime("%m-%d")
    entry = f"{stamp} {line}"

    lines = _trim_lines(load(tid).splitlines() + [entry])
    try:
        with open(_path(tid), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except Exception:
        return False


def compact_from_rounds(rounds):
    """没有 AI 也能用的兜底：把最近几轮压成关键词一行"""
    words = []
    for u, b in rounds[-ROUNDS_PER_DIGEST:]:
        for text in (u, b):
            for w in re.findall(r"[\u4e00-\u9fa5]{2,4}", text or ""):
                if w not in words:
                    words.append(w)
    return "、".join(words[:8]) if words else ""


async def update(tid, rounds, summarize=None):
    """把最近 rounds 浓缩一行写进文档

    summarize: 可选，异步函数 (文本) -> 一行摘要；没有就用兜底规则。
    """
    if not rounds or len(rounds) < ROUNDS_PER_DIGEST:
        return False

    line = ""
    if summarize is not None:
        try:
            convo = "\n".join(f"他：{u}\n她：{b}" for u, b in rounds[-ROUNDS_PER_DIGEST:])
            line = await summarize(convo)
        except Exception as e:
            log_api(f"[浓缩] AI 摘要失败，用兜底: {e}")
    if not line:
        line = compact_from_rounds(rounds)
    if not line:
        return False

    ok = append(tid, line)
    if ok:
        log_api(f"[浓缩] {str(tid)[:8]}: {line[:30]}")
    return ok


def describe(tid):
    """给 prompt 用：文档内容；没有就空"""
    text = load(tid)
    return text if text else ""

async def maybe_condense(tid, summarize=None, rng=None):
    """超过 30 轮后，把溢出缓冲里的旧对话浓缩成一行（v14.1-D3）

    返回这次是否写入了一行。
    """
    from ..core import state as cfg

    buf = cfg.digest_pending.get(str(tid)) or []
    if len(buf) < ROUNDS_PER_DIGEST:
        return False

    chunk = buf[:ROUNDS_PER_DIGEST]
    del buf[:ROUNDS_PER_DIGEST]

    ok = await update(tid, chunk, summarize)
    if ok:
        log_api(f"[浓缩] {str(tid)[:8]} 溢出 {len(chunk)} 轮，已写入记录")
    return ok