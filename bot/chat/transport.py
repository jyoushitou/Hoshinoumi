# ===================== QQ 传输适配器 =====================
# v5-R4：把 send_private_msg / send_group_msg 包成 Transport 端口
# 行为不变：内部仍然走原来的发送函数（含发送锁、日志）

import json

from ..core import state as cfg
from ..ports.transport import Transport, Target, Segment
from .send import send_private_msg, send_group_msg


class QqTransport:
    """QQ 实现：一条消息 = 多个消息段"""

    def __init__(self, ws):
        self.ws = ws

    def _segments(self, segments):
        return [{"type": s.type, "data": dict(s.data)} for s in segments]

    async def send(self, target: Target, segments: list) -> None:
        msg = self._segments(segments)
        if target.kind == "group":
            await send_group_msg(target.id, msg, self.ws)
        else:
            await send_private_msg(target.id, msg, self.ws)

    async def poke(self, target: Target, user_id) -> None:
        """戳一戳（NapCat send_poke）"""
        params = {"user_id": user_id}
        if target.kind == "group":
            params["group_id"] = target.id
        # v17.2：走出站口（全局锁 + 断线入队）
        from ..egress.outbound import get_outbound
        out = get_outbound()
        out.bind(self.ws)
        await out.send("send_poke", params, label="戳一戳", kind="poke")


assert isinstance(QqTransport(None), Transport)
