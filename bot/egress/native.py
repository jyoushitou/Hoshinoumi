# ===================== WebSocket 出站 native（v33.5.1） =====================

from ..ports.transport import Target, Transport


class WebSocketTransport:
    name = "websocket"

    async def send(self, target, segments):
        from ..chat.send import send_group_msg, send_private_msg
        msg = [{"type": s.type, "data": s.data} for s in segments]
        if target.kind == "group":
            await send_group_msg(int(target.id), msg, None)
        else:
            await send_private_msg(str(target.id), msg, None)

    async def poke(self, target, user_id):
        return None


assert isinstance(WebSocketTransport(), Transport)
