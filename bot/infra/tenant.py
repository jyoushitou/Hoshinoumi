# ===================== 租户上下文（v23.2） =====================
# v23 起所有业务查询必须带 user_id；本模块只做规范化/校验，不依赖数据库。

OWNER_ID = "__owner__"
SYSTEM_ID = "__system__"


class TenantError(ValueError):
    """缺少 user_id 或跨租户访问"""


def require(user_id):
    """v23.2 红线：没有 user_id 直接报错，不默认成主人"""
    if user_id is None or str(user_id).strip() == "":
        raise TenantError("user_id 不能为空")
    return str(user_id).strip()


def owner():
    return OWNER_ID


def is_owner(user_id):
    return str(user_id or "") == OWNER_ID


def require_owner(user_id):
    uid = require(user_id)
    if uid != OWNER_ID:
        raise TenantError("需要 owner 权限")
    return uid


def scoped(user_id):
    """把可能为空的旧调用规范成 owner；仅供旧代码迁移期使用。"""
    return str(user_id).strip() if user_id and str(user_id).strip() else OWNER_ID
