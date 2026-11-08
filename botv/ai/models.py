# ===================== 模型适配器 =====================
# v5-R3：把现有的 call_deepseek / call_doubao 包成 ChatModel 端口
# 行为不变：内部仍然走原来的函数（含超时、重试、落库）

from ..ports.models import ChatModel, ChatRequest, ChatReply
from .client import call_deepseek, call_doubao


class DeepSeekModel:
    """DeepSeek 适配器"""

    name = "deepseek"
    supports_vision = False  # 暂不支持多模态；接入 VL 后改这里

    async def complete(self, req: ChatRequest):
        text = await call_deepseek(
            req.messages,
            max_tokens=req.max_tokens,
            target_id=req.target_id or None,
        )
        if not text:
            return None  # 交给上层降级
        return ChatReply(text=text, model=self.name)


class DoubaoModel:
    """豆包适配器（兜底模型）"""

    name = "doubao"
    supports_vision = False

    async def complete(self, req: ChatRequest):
        text = await call_doubao(
            req.messages,
            max_tokens=req.max_tokens,
            target_id=req.target_id or None,
        )
        if not text:
            return None
        return ChatReply(text=text, model=self.name)


# 显式声明它们满足端口（运行时用 isinstance 检查，测试里会验证）
assert isinstance(DeepSeekModel(), ChatModel)
assert isinstance(DoubaoModel(), ChatModel)
