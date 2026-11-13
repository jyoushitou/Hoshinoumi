# ===================== AI 生成端口（v21.6） =====================
# diary / schedule 不直接 import ai.client；由 ai 层注册生成能力。
_impl = {"text": None}


def register_text(fn):
    _impl["text"] = fn
    return fn


async def generate_text(messages, max_tokens=1500, target_id=None):
    fn = _impl["text"]
    if fn is None:
        # 兼容：测试或极早调用时按需加载一次，正常启动会在 ai.client 导入时注册
        from ..ai.client import register_diary_text
        register_diary_text()
        fn = _impl["text"]
    if fn is None:
        raise RuntimeError("AI 文本生成端口未注册")
    return await fn(messages, max_tokens=max_tokens, target_id=target_id)
