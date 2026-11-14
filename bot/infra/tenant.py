# ===================== 租户上下文（v23.2） =====================
# v23 起所有业务查询必须带 user_id；本模块只做规范化/校验，不依赖数据库。

OWNER_ID = "__owner__"
SYSTEM_ID = "__system__"


def owner_id():
    """v23.5：owner user_id 直接是 MASTER_QQ；未配置时退回旧 __owner__。"""
    try:
        from ..config import MASTER_QQ
        q = int(MASTER_QQ or 0)
        return str(q) if q > 0 else OWNER_ID
    except Exception:
        return OWNER_ID


class TenantError(ValueError):
    """缺少 user_id 或跨租户访问"""


def require(user_id):
    """v23.2 红线：没有 user_id 直接报错，不默认成主人"""
    if user_id is None or str(user_id).strip() == "":
        raise TenantError("user_id 不能为空")
    return str(user_id).strip()


def owner():
    return owner_id()


def is_owner(user_id):
    uid = str(user_id or "")
    return uid in (OWNER_ID, owner_id())


def require_owner(user_id):
    uid = require(user_id)
    if not is_owner(uid):
        raise TenantError("需要 owner 权限")
    return uid


def scoped(user_id):
    """把可能为空的旧调用规范成 owner；仅供旧代码迁移期使用。"""
    return str(user_id).strip() if user_id and str(user_id).strip() else owner_id()
