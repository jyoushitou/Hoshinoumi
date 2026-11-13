# ===================== 通知事件（v12-A16） =====================
# NapCat 除了消息还会发 notice：戳一戳、撤回、加好友之类。
# 现在只处理「戳一戳」，被戳就回戳一下。

from ..log import log_api, log_system

# 回戳的几种反应：多数直接回戳，偶尔配一句话
POKE_BACK_PROB = 0.85


def is_poke(d):
    """是不是「有人戳了她」"""
    if not isinstance(d, dict):
        return False
    if d.get("post_type") != "notice":
        return False
    if d.get("notice_type") != "notify":
        return False
    return d.get("sub_type") == "poke"


async def handle_notice(d, ws, self_qq=0, send_action=None):
    """处理通知事件；返回是否处理了"""
    if is_poke(d):
        target = str(d.get("target_id", ""))
        # 只回应「戳的是我」，不是所有 poke 都回
        if self_qq and target != str(self_qq):
            return False

        uid = str(d.get("user_id", ""))
        gid = d.get("group_id")
        if not uid:
            return False

        if gid:
            action, params = "group_poke", {"group_id": gid, "user_id": uid}
        else:
            action, params = "friend_poke", {"user_id": uid}

        log_system(f"被戳: {uid} -> 回戳")
        if send_action is not None:
            try:
                await send_action(action, params, ws, "回戳")
            except Exception as e:
                log_api(f"[戳一戳] 回戳失败: {e}")
                return False
        return True
    return False
