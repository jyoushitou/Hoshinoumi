# ===================== 工具调用（v13-U22 / F34） =====================
# 让她自己决定「要不要去查/去记」。
#
# 协议（写进人设）：
#     需要工具时，单独一行输出：@tool: 工具名(参数)
#     拿到结果后，用自然的语气接下去，不要再输出 @tool。
#
# 只做一件事：解析 → 执行 → 把结果还给模型。最多一轮，防止无限套娃。

import re

from ..log import log_api

_CALL = re.compile(r"@tool:\s*([a-z_]+)\s*\((.*?)\)", re.S)

# 工具名 → 说明（会写进 prompt）
TOOLS = {
    "recall": "检索记忆，参数是要搜的词，返回最相关的几条",
    "remember": "把一件重要的事记下来，参数是一句话",
    "agenda_add": "记一条日程/待办，参数是带时间的话",
    "search_images": "搜图库，参数是关键词，返回找到几张",
}


def parse_call(text):
    """从模型输出里找出工具调用，返回 (名字, 参数, 去掉调用行后的正文)"""
    if not text or "@tool:" not in text:
        return None, None, text
    m = _CALL.search(text)
    if not m:
        return None, None, text
    name, arg = m.group(1).strip(), m.group(2).strip()
    body = _CALL.sub("", text).strip()
    return name, arg, body


def tool_prompt():
    """给 prompt 用的工具说明"""
    lines = ["【你能用的工具】（需要时单独一行输出 @tool: 名字(参数)，拿到结果再正常回话）"]
    for name, desc in TOOLS.items():
        lines.append(f"- {name}：{desc}")
    return "\n".join(lines)


async def run_tool(name, arg, tid):
    """执行一个工具，返回给模型看的字符串"""
    name = (name or "").strip()
    arg = (arg or "").strip()
    log_api(f"[工具] {name}({arg[:30]})")

    try:
        if name == "recall":
            from ..memory.retrieval import retrieve
            from ..infra.repo_memory import load_memories_for_search
            rows = load_memories_for_search(str(tid), limit=200)
            hits = retrieve(arg, rows, top_k=3) if rows and arg else []
            if not hits:
                return "没找到相关的记忆"
            return "；".join(m.get("summary", "") for m, _s in hits)

        if name == "remember":
            from ..infra.repo_memory import add_event_to_db
            if not arg:
                return "没给内容"
            add_event_to_db(str(tid), arg[:200], tags="她记的", kind="event", importance=4)
            return f"记下了：{arg[:40]}"

        if name == "agenda_add":
            from ..life.agenda import extract, add
            item = extract(arg)
            if not item:
                return "没听出时间，需要更明确的说法"
            add(item)
            return f"记进日程了：{item['t'][:40]}"

        if name == "search_images":
            from ..image import get_best_image
            fp = await get_best_image(arg.split(","), str(tid)) if arg else None
            return "找到一张图" if fp else "图库里没有合适的"

    except Exception as e:
        log_api(f"[工具] {name} 失败: {e}")
        return "工具出错了"

    return f"没有这个工具：{name}"
