# ===================== WebSocket 握手 token（v26.0） =====================
# 默认不启用；设置 NAO_WS_TOKEN 后，NapCat 的 WS URL 需带 ?token=...
# 只做本机/可信入口的轻量边界，不替代公网鉴权。

import os
from urllib.parse import parse_qs, urlsplit


def token_ok(path, expected=None):
    expected = os.getenv("NAO_WS_TOKEN", "") if expected is None else expected
    if not expected:
        return True
    try:
        q = parse_qs(urlsplit(path or "").query)
    except Exception:
        return False
    return q.get("token", [""])[0] == expected
