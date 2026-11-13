# ===================== 语音/文字分段解析（v19.3） =====================
# AI 可以用【语音】…【/语音】标记要念的段，【文字】…【/文字】标记文字段。
# 未闭合/空段降级为文字；标记绝不出现在发送内容里。

import re

VOICE_OPEN = "【语音】"
VOICE_CLOSE = "【/语音】"
TEXT_OPEN = "【文字】"
TEXT_CLOSE = "【/文字】"


def _clean(s):
    return (s or "").strip()


def parse(text):
    """返回 [(kind, text)]，kind 为 text/voice；按原顺序"""
    s = str(text or "")
    out = []
    i = 0
    n = len(s)
    while i < n:
        # 找最近的左标记
        vi = s.find(VOICE_OPEN, i)
        ti = s.find(TEXT_OPEN, i)
        if vi < 0 and ti < 0:
            tail = _clean(s[i:])
            if tail:
                out.append(("text", tail))
            break
        if vi < 0 or (ti >= 0 and ti < vi):
            # 文字段：可选结束标记；没有就吃到下一个语音标记/结尾
            start = ti + len(TEXT_OPEN)
            close = s.find(TEXT_CLOSE, start)
            if close >= 0:
                body = s[start:close]
                i = close + len(TEXT_CLOSE)
            else:
                nxt = s.find(VOICE_OPEN, start)
                body = s[start:nxt if nxt >= 0 else n]
                i = nxt if nxt >= 0 else n
            body = _clean(body.replace(VOICE_OPEN, "").replace(VOICE_CLOSE, ""))
            if body:
                out.append(("text", body))
            continue
        # 语音段
        start = vi + len(VOICE_OPEN)
        close = s.find(VOICE_CLOSE, start)
        if close >= 0:
            body = s[start:close]
            i = close + len(VOICE_CLOSE)
        else:
            # 未闭合：去掉标记，剩余按文字处理
            body = s[start:]
            i = n
            body = _clean(body)
            if body:
                out.append(("text", body))
            break
        body = _clean(body.replace(TEXT_OPEN, "").replace(TEXT_CLOSE, ""))
        if body:
            out.append(("voice", body))
    if not out:
        plain = strip_markers(s)
        if plain:
            out.append(("text", plain))
    return out


def strip_markers(text):
    s = str(text or "")
    for m in (VOICE_OPEN, VOICE_CLOSE, TEXT_OPEN, TEXT_CLOSE):
        s = s.replace(m, "")
    return s.strip()


def to_text(text):
    """把标记内容按原顺序拼成纯文字（群聊/代码模式/降级用）"""
    parts = [body for _kind, body in parse(text)]
    return "\n".join(parts).strip()
