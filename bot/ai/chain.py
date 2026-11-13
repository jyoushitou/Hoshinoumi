# ===================== 模型链 =====================
# v5-R3：按顺序尝试多个 ChatModel，第一个成功即返回
# 与 get_character_reply 里的「DS 失败转豆包」是同一语义，只是抽成了端口组合

from ..log import log_api


class FallbackChain:
    """模型链：依次尝试，全部失败返回 None"""

    def __init__(self, models):
        self._models = list(models)

    @property
    def models(self):
        return list(self._models)

    def supports_vision(self) -> bool:
        """只要有一个模型能看图，这条链就能处理图片"""
        return any(getattr(m, "supports_vision", False) for m in self._models)

    async def complete(self, req):
        for m in self._models:
            try:
                reply = await m.complete(req)
            except Exception as e:  # 单个模型炸了不影响下一个
                log_api(f"[模型链] {getattr(m, 'name', m)} 异常: {e}")
                continue
            if reply:
                return reply
            log_api(f"[模型链] {getattr(m, 'name', m)} 无回复，尝试下一个")
        return None
