# ===================== 租户仓储门面（v23.2） =====================
# v23.2 起，新代码只走这里：user_id 必填，缺失直接 TenantError。
# 旧仓储保留 owner 默认值用于迁移期；API/命令在 v23.3 切到本门面。

from . import repo_conversation, repo_memory, tenant


def memory_events(tid, user_id, **kwargs):
    uid = tenant.require(user_id)
    return repo_memory.load_events_from_db(tid, user_id=uid, **kwargs)


def memory_search(tid, user_id, **kwargs):
    uid = tenant.require(user_id)
    return repo_memory.load_memories_for_search(tid, user_id=uid, **kwargs)


def conversation_recent(target_id, user_id, **kwargs):
    uid = tenant.require(user_id)
    return repo_conversation.recent(target_id, user_id=uid, **kwargs)


def conversation_append(target_id, user_id, **kwargs):
    uid = tenant.require(user_id)
    kwargs["user_id"] = uid
    return repo_conversation.append(target_id=target_id, **kwargs)


def cron_list(user_id, **kwargs):
    uid = tenant.require(user_id)
    from ..schedule import cron
    return cron.list_tasks(user_id=uid, **kwargs)


def cron_add(target_id, user_id, **kwargs):
    uid = tenant.require(user_id)
    from ..schedule import cron
    return cron.add(target_id, user_id=uid, **kwargs)


def diary_get(target_id, date_str, user_id):
    uid = tenant.require(user_id)
    from ..diary import store
    return store.get_diary_from_db(target_id, date_str, user_id=uid)
