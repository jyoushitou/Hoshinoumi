# ===================== life 包（v9） =====================
# 她不在你面前时的生活：状态向量 + 每日生活事件

from .state import (  # noqa: F401
    BASE,
    default_state,
    clamp,
    tick,
    on_talk,
    on_ignored,
    describe,
    load,
    save,
    to_json,
    from_json,
)
