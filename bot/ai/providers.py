# ===================== native model providers（v29.1/v29.2） =====================
# 核心 native：DeepSeek / 豆包。它们不实现 PluginManifest，不进入插件表。

from ..ports.models import ModelProvider, ModelReply, ModelRequest
from ..core.types import Fallback
from .client import call_deepseek, call_doubao


class DeepSeekProvider:
    name = "deepseek"

    def capabilities(self):
        return {"text"}

    async def complete(self, req: ModelRequest):
        text = await call_deepseek(
            req.messages,
            max_tokens=req.max_tokens,
            target_id=req.target_id or None,
        )
        if not text:
            return None
        return ModelReply(text=text, model=self.name)


assert isinstance(DeepSeekProvider(), ModelProvider)


class DoubaoProvider:
    name = "doubao"

    def capabilities(self):
        return {"text"}

    async def complete(self, req: ModelRequest):
        text = await call_doubao(
            req.messages,
            max_tokens=req.max_tokens,
            target_id=req.target_id or None,
        )
        if not text:
            return None
        return ModelReply(text=str(text), model=self.name,
                          fallback=isinstance(text, Fallback))


assert isinstance(DoubaoProvider(), ModelProvider)
