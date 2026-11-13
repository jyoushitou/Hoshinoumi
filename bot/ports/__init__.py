# ===================== ports 包 =====================
# 端口（协议）定义：只放 Protocol 与数据结构，零依赖、零副作用
# 规则：这里不许 import 任何实现模块（ai/chat/infra/server 都不行）

from .models import ChatModel, ChatRequest, ChatReply  # noqa: F401
from .transport import Transport, Segment, Target  # noqa: F401
from .memory import MemoryStore, Embedder, Retriever, MemoryItem, Query  # noqa: F401
from .clock import Clock  # noqa: F401
