# ===================== 调度策略（v17.1.0） =====================
# 超时、重试、熔断——都是纯逻辑，不做 IO，方便单独测。
#
# 规则（来自 v17 计划）：
#   - 超时：到点取消任务，**不重试**（超时说明这条路径有问题，重试只会加剧）
#   - 失败：可重试 retries 次，间隔指数退避
#   - 熔断：同一 kind 连续失败 3 次 → 停 1 小时，期间直接拒绝

import time

RETRY_BASE_DELAY = 2.0          # 首次重试等待（秒）
RETRY_MAX_DELAY = 30.0          # 退避上限
BREAKER_THRESHOLD = 3           # 连续失败几次熔断
BREAKER_COOLDOWN = 3600.0       # 熔断时长（1 小时）


class Breaker:
    """按 kind 的熔断器"""

    def __init__(self, threshold=BREAKER_THRESHOLD, cooldown=BREAKER_COOLDOWN):
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = {}        # kind -> 连续失败次数
        self._open_until = {}      # kind -> 熔断到期时间戳
        self._total_open = 0       # 熔断次数（观测）

    # ---------- 查询 ----------

    def is_open(self, kind, now=None):
        """该 kind 是否处于熔断中"""
        until = self._open_until.get(kind)
        if not until:
            return False
        if (now or time.time()) >= until:
            # 到期自动恢复
            self._open_until.pop(kind, None)
            self._failures.pop(kind, None)
            return False
        return True

    def remaining(self, kind, now=None):
        """还要等几秒（未熔断返回 0）"""
        until = self._open_until.get(kind)
        if not until:
            return 0.0
        return max(0.0, until - (now or time.time()))

    def failures(self, kind):
        return self._failures.get(kind, 0)

    # ---------- 记录 ----------

    def record_success(self, kind):
        """成功：清零连续失败"""
        self._failures.pop(kind, None)
        self._open_until.pop(kind, None)

    def record_failure(self, kind, now=None):
        """失败：累加，到阈值就熔断；返回是否刚刚熔断"""
        now = now or time.time()
        n = self._failures.get(kind, 0) + 1
        self._failures[kind] = n
        if n >= self.threshold and not self.is_open(kind, now):
            self._open_until[kind] = now + self.cooldown
            self._total_open += 1
            return True
        return False

    def reset(self):
        self._failures.clear()
        self._open_until.clear()

    def stats(self):
        return {
            "open_kinds": sorted(k for k in self._open_until if self.is_open(k)),
            "failures": dict(self._failures),
            "total_open": self._total_open,
        }


def retry_delay(attempt, base=None, cap=None):
    """第 attempt 次重试前等多久（attempt 从 1 开始）：2, 4, 8, … 封顶

    base/cap 不传时**运行时**读模块常量——这样测试里改常量就能生效。
    """
    if attempt <= 0:
        return 0.0
    base = RETRY_BASE_DELAY if base is None else base
    cap = RETRY_MAX_DELAY if cap is None else cap
    return min(cap, base * (2 ** (attempt - 1)))


def should_retry(ev, error, attempt):
    """要不要重试

    - 超时不重试（TimeoutError）
    - 已用完次数不重试
    - 其余可重试
    """
    import asyncio

    if isinstance(error, asyncio.TimeoutError):
        return False
    return attempt < max(1, int(getattr(ev, "retries", 1)))


def classify(error):
    """给日志用的错误分类"""
    import asyncio

    if isinstance(error, asyncio.TimeoutError):
        return "timeout"
    if isinstance(error, asyncio.CancelledError):
        return "cancelled"
    if isinstance(error, (KeyError, ValueError, TypeError)):
        return "bad_input"
    return "error"
