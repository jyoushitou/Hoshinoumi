# ===================== 阻塞调用线程池（v17.0.1） =====================
# asyncio 是单线程事件循环：任何同步阻塞调用都会卡住整个程序。
#
#     r = requests.post(...)          # ← 这 3 秒里程序什么都干不了
#     r = await run_blocking(requests.post, ...)   # ← 正确写法
#
# 约束：
#   - 线程数是自限的（默认 3），不是平台限制
#   - 超时只放弃等待，**不杀线程**（Python 杀不掉线程）
#   - 线程池里的函数必须是线程安全的（DB 用线程本地连接）

import asyncio
import functools
import os
from concurrent.futures import ThreadPoolExecutor

from ..log import log_api

POOL_SIZE = int(os.getenv("NAO_TASK_THREADS", "3"))
DEFAULT_TIMEOUT = float(os.getenv("NAO_BLOCKING_TIMEOUT", "120"))

_pool = ThreadPoolExecutor(max_workers=POOL_SIZE, thread_name_prefix="nao-block")


async def run_blocking(fn, *args, timeout=DEFAULT_TIMEOUT, name=None, **kwargs):
    """在线程池里执行同步函数，返回其结果

    - 不阻塞事件循环（其他协程照常调度）
    - 超时抛 asyncio.TimeoutError；线程会自己跑完，结果丢弃
    - 同步函数抛的异常会原样透传
    """
    label = name or getattr(fn, "__name__", "blocking")
    loop = asyncio.get_running_loop()
    fut = loop.run_in_executor(_pool, functools.partial(fn, *args, **kwargs))
    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        log_api(f"[blocking:{label}] 超时 {timeout:.0f}s（线程仍在跑，结果丢弃）")
        raise
    except Exception as e:
        log_api(f"[blocking:{label}] 失败: {e}")
        raise
