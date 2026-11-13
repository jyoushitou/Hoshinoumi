# ===================== 模型端口 =====================
# 一次补全请求 / 一次补全结果 / 模型能力声明
# 目的：DeepSeek 与豆包共用同一个接口，重试与降级逻辑只写一处

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass
class ChatRequest:
    """一次补全请求"""
    messages: list                 # [{"role": "system|user|assistant", "content": str}]
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    target_id: str = ""            # 记忆/日志归属对象
    images: list = field(default_factory=list)  # 多模态：data URI 或 URL 列表


@dataclass
class ChatReply:
    """一次补全结果"""
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    raw: Optional[dict] = None


@runtime_checkable
class ChatModel(Protocol):
    """模型端口：DeepSeek / 豆包 / 未来的任何模型都实现它"""
    name: str
    supports_vision: bool

    async def complete(self, req: ChatRequest) -> Optional[ChatReply]:
        """返回补全结果；失败返回 None（由上层决定重试还是降级）"""
        ...
