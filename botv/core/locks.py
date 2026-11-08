# ===================== 并发控制（v6-E26） =====================
# 两个东西：
#   1) 按对象加锁——同一个人串行、不同人可以并行
#   2) 模型调用信号量——最多 N 个请求同时在飞

import asyncio
import time

import botv.core.state as cfg

# 每个对象一把锁，用完闲置就回收
_last_used = {}

# 同时在飞的模型请求上限（5 路对话够用，也压得住 API 费用）
MAX_CONCURRENT_MODEL_CALLS = 5

_model_sem = None
_model_loop = None


def get_target_lock(tid):
    """取某个对象的锁（没有就建一个）"""
    lock = cfg.target_locks.get(tid)
    if lock is None:
        lock = asyncio.Lock()
        cfg.target_locks[tid] = lock
    _last_used[tid] = time.time()
    return lock


def cleanup_idle_locks(max_idle=600):
    """回收闲置超过 max_idle 秒且没有在用的锁"""
    now = time.time()
    removed = 0
    for tid in list(cfg.target_locks):
        lock = cfg.target_locks[tid]
        if lock.locked():  # 正在用，跳过
            continue
        if now - _last_used.get(tid, 0) > max_idle:
            cfg.target_locks.pop(tid, None)
            _last_used.pop(tid, None)
            removed += 1
    return removed


def model_semaphore():
    """模型调用信号量（按事件循环懒创建，避免跨 loop 复用报错）"""
    global _model_sem, _model_loop
    loop = asyncio.get_running_loop()
    if _model_sem is None or _model_loop is not loop:
        _model_sem = asyncio.Semaphore(MAX_CONCURRENT_MODEL_CALLS)
        _model_loop = loop
    return _model_sem
