# ===================== 最近消息缓存（v18.6） =====================
# 引用回复时先查这里，命中就不发 get_msg。
#
# 只存文本/描述，不存图片二进制；环形 200 条，进程内。
# message_id 统一转成 str，避免 NapCat 有时给 int 有时给 str。

from collections import OrderedDict

MAX_MESSAGES = 200
_messages = OrderedDict()   # {str(message_id): (sender, text)}


def remember(mid, sender, text):
    """记一条消息；空文本/空 id 不记"""
    if mid is None:
        return False
    key = str(mid)
    text = (text or "").strip()
    if not key or not text:
        return False
    _messages[key] = (str(sender or "").strip(), text[:500])
    _messages.move_to_end(key)
    while len(_messages) > MAX_MESSAGES:
        _messages.popitem(last=False)
    return True


def get(mid):
    """取一条；返回 (sender, text) 或 None"""
    if mid is None:
        return None
    return _messages.get(str(mid))


def clear():
    _messages.clear()


def size():
    return len(_messages)
