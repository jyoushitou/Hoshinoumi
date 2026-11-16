# ===================== 核心 native 默认路由（v33.6.1） =====================

from ..ports.route import Candidate, RouteKey

DEFAULTS = {
    "model": "deepseek",
    "memory": "bm25",
    "channel": "qq",
    "tool": "native",
    "storage": "sql",
    "scheduler": "asyncio",
    "outbound": "websocket",
}


class NativeRouteRegistry:
    def resolve(self, key):
        return Candidate("native", DEFAULTS.get(key.layer, "native"))

    def candidates(self, key):
        return [self.resolve(key)]
