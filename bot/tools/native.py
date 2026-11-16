# ===================== 现有工具 native 包装（v33.2.1） =====================

from ..ports.tool import Tool


class FunctionTool:
    """把一个普通函数包成 Tool；现有工具可逐个登记。"""

    def __init__(self, spec, fn=None):
        self.spec = spec
        self.name = spec.name
        self.schema = spec.schema
        self.permissions = set(spec.permissions)
        self._fn = fn

    async def invoke(self, user_id, args):
        if self._fn is None:
            return {"ok": False, "error": "not wired"}
        out = self._fn(user_id, args)
        if hasattr(out, "__await__"):
            out = await out
        return out if isinstance(out, dict) else {"ok": True, "result": out}


class EchoTool(FunctionTool):
    def __init__(self):
        from ..ports.tool import ToolSpec
        super().__init__(ToolSpec("echo", "回显", {}, ()),
                         lambda uid, args: {"ok": True, "text": args.get("text", "")})


assert isinstance(EchoTool(), Tool)
