# ===================== QQ / NapCat 通道（v33.1） =====================
# 包装现有 chat.send；start/stop 只维护状态，不接管 ingress。

from ..ports.channel import Channel


class QQChannel:
    name = "qq"

    def __init__(self):
        self.started = False
        self._handler = None

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False

    async def send(self, target, text, is_group=False):
        if not self.started:
            return False
        from ..chat import send as sender
        msg = [{"type": "text", "data": {"text": text}}]
        try:
            if is_group:
                await sender.send_group_msg(int(target), msg, None)
            else:
                await sender.send_private_msg(str(target), msg, None)
            return True
        except Exception:
            return False

    def on_message(self, handler):
        self._handler = handler


assert isinstance(QQChannel(), Channel)
