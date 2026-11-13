# ===================== 日志模块 =====================
# 五级日志：系统/接收/发送/接口/异常
#
# v17.14（债一）：**文件优先，刷库次之**
#   - log_* 只负责：控制台 + 文件（txtlog），同步、不会抛
#   - 写数据库丢进有界队列，由后台线程尽力而为
#   - 数据库挂了，日志照样有；排障时最需要的东西不会先失效
#
# 依赖方向：log 不再在 import 时依赖 db（只在刷库线程里按需导入）。

import queue
import threading
from .core import clock

_QUEUE_MAX = 2000
_queue = queue.Queue(maxsize=_QUEUE_MAX)
_stats = {"dropped": 0, "flushed": 0, "failed": 0}
_flusher = {"thread": None, "stop": threading.Event()}


def _stamp():
    """日志时间戳：固定东八区（服务器 TZ=UTC 时也不会差 8 小时）"""
    return clock.fmt_hms()


_writer = {"fn": None}


def register_db_writer(fn):
    """由启动装配注入 DB writer；log 本身不 import infra/db"""
    _writer["fn"] = fn


def _db_writer():
    return _writer["fn"]


def _flusher_loop():
    """后台线程：把队列里的日志刷进数据库；失败只计数，不抛"""
    writer = None
    while not _flusher["stop"].is_set():
        try:
            tag, msg = _queue.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            if writer is None:
                writer = _db_writer()
            writer(tag, msg)
            _stats["flushed"] += 1
        except Exception:
            _stats["failed"] += 1
            writer = None          # 下次重试导入（数据库可能还没就绪）
        finally:
            try:
                _queue.task_done()
            except Exception:
                pass


def _ensure_flusher():
    t = _flusher["thread"]
    if t is not None and t.is_alive():
        return t
    _flusher["stop"].clear()
    t = threading.Thread(target=_flusher_loop, name="nao-log-flush", daemon=True)
    t.start()
    _flusher["thread"] = t
    return t


def stop_flusher(timeout=2.0):
    """测试/退出时停掉刷库线程"""
    _flusher["stop"].set()
    t = _flusher["thread"]
    if t is not None and t.is_alive():
        t.join(timeout=timeout)
    _flusher["thread"] = None


def flush_stats():
    return dict(_stats, pending=_queue.qsize())


def _to_db(tag, msg):
    """入队；队满就丢最旧的（日志不能反过来拖垮主流程）"""
    _ensure_flusher()
    try:
        _queue.put_nowait((tag, msg))
    except queue.Full:
        _stats["dropped"] += 1
        try:                       # 丢掉队首一条，给新日志腾位置
            _queue.get_nowait()
            _queue.task_done()
        except Exception:
            pass
        try:
            _queue.put_nowait((tag, msg))
        except Exception:
            pass


def _txt(tag, m):
    """写一份到 txt 文件（失败静默）"""
    try:
        from .infra import txtlog

        txtlog.write(tag, m)
    except Exception:
        pass


def _emit(tag, m, fmt):
    print(fmt)
    _txt(tag, m)
    _to_db(tag, m)


def log_system(m):
    """系统级日志：初始化、定时任务、状态变更等"""
    _emit("系统", m, f"【系统】{_stamp()}|{m}")


def log_recv(m):
    """接收日志：收到的QQ消息"""
    _emit("接收", m, f"【接收】{_stamp()}|{m}")


def log_send(m):
    """发送日志：发送的消息内容"""
    _emit("发送", m, f"【发送】{_stamp()}|{m}")


def log_api(m):
    """接口日志：API调用、图片处理、CLIP分析等"""
    _emit("接口", m, f"【接口】{_stamp()}|{m}")


def log_err(m):
    """异常日志：捕获到的错误和异常"""
    _emit("异常", m, f"【异常】{_stamp()}|{m}")



