# 测试

import sys
import types
import unittest


def _stub_missing_deps():
    """缺依赖就打个桩（必须在导入 bot 之前调用）"""
    def module(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    try:
        import pymysql  # noqa: F401
    except ImportError:
        module("pymysql")
        module("pymysql.cursors", DictCursor=object)
        sys.modules["pymysql"].cursors = sys.modules["pymysql.cursors"]
        sys.modules["pymysql"].connect = lambda **kw: None

    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            module(name, **attrs)

    try:
        import requests  # noqa: F401
    except ImportError:
        module("requests", Session=lambda: None, get=lambda *a, **k: None,
               post=lambda *a, **k: None)


_stub_missing_deps()

from datetime import datetime
from bot.config import CST


import unittest

class TestBaselineBubble(unittest.TestCase):
    """基线：气泡之间的间隔与数量上限"""

    def test_bubble_delay_range(self):
        """气泡间隔：落在 1.5~3.0 秒"""
        from bot.chat.send import bubble_delay

        samples = [bubble_delay() for _ in range(300)]
        self.assertGreaterEqual(min(samples), 1.5)
        self.assertLessEqual(max(samples), 3.0)
        self.assertGreater(max(samples) - min(samples), 0.8, "应当有随机浮动")

    def test_bubble_delay_uniform(self):
        """气泡间隔是均匀分布（均值接近中点 2.25）"""
        from bot.chat.send import bubble_delay

        samples = [bubble_delay() for _ in range(2000)]
        avg = sum(samples) / len(samples)
        self.assertAlmostEqual(avg, 2.25, delta=0.1, msg="均匀分布均值约 2.25")

    def test_max_reply_lines(self):
        """v18.10：一次回复最多 4 个气泡（超出合并）"""
        from bot.chat.reply import MAX_REPLY_LINES

        self.assertEqual(MAX_REPLY_LINES, 4)

def _at(hour, minute=0):
    return datetime(2026, 11, 10, hour, minute, tzinfo=CST)


class TestBaselineDelay(unittest.TestCase):
    """基线：回复延迟按时段的取值范围"""

    def test_delay_range_bands(self):
        """每个时段的区间必须与 BANDS 一致"""
        from bot.chat.timing import delay_range

        expected = {
            3: (20, 180),    # 凌晨
            7: (10, 60),     # 清晨
            13: (5, 30),     # 白天
            20: (8, 60),     # 晚上
            23: (20, 120),   # 深夜
        }
        for hour, (lo, hi) in expected.items():
            got = delay_range(_at(hour))
            self.assertEqual(got, (lo, hi), f"{hour} 点应落在 {lo}~{hi} 秒")

    def test_delay_range_boundaries(self):
        """时段边界：6 点属于清晨，9 点属于白天，18 点属于晚上"""
        from bot.chat.timing import delay_range

        self.assertEqual(delay_range(_at(6)), (10, 60))
        self.assertEqual(delay_range(_at(9)), (5, 30))
        self.assertEqual(delay_range(_at(18)), (8, 60))
        self.assertEqual(delay_range(_at(0)), (20, 180))

    def test_reply_delay_stays_in_band(self):
        """200 次采样都要落在当前时段的区间内"""
        from bot.chat.timing import reply_delay, delay_range

        now = _at(13)                      # 白天：5~30 秒
        lo, hi = delay_range(now)
        samples = [reply_delay(now) for _ in range(200)]

        self.assertGreaterEqual(min(samples), lo)
        self.assertLessEqual(max(samples), hi)
        self.assertGreater(max(samples) - min(samples), 1.0, "应当有随机浮动")

    def test_reply_delay_skewed_short(self):
        """平方分布：大多数延迟靠近下界，中位数明显小于区间中点"""
        from bot.chat.timing import reply_delay, delay_range

        now = _at(13)
        lo, hi = delay_range(now)
        mid = (lo + hi) / 2

        samples = sorted(reply_delay(now) for _ in range(400))
        median = samples[len(samples) // 2]

        self.assertLess(median, mid, "中位数应低于区间中点（偏向短端）")
        # 且大部分样本落在前半段
        front_half = sum(1 for s in samples if s <= mid)
        self.assertGreater(front_half / len(samples), 0.6, "至少 60% 落在前半段")

class TestBaselineGroupGate(unittest.TestCase):
    """基线：群聊闸门的三个数字与概率区间"""

    def test_gate_constants(self):
        """冷却 20 秒、窗口 60 秒、窗口内最多 6 条、@ 最小间隔 3 秒"""
        from bot.chat import handler as H

        self.assertEqual(H.GROUP_COOLDOWN, 20)
        self.assertEqual(H.GROUP_WINDOW, 60)
        self.assertEqual(H.GROUP_WINDOW_MAX, 6)
        self.assertEqual(H.GROUP_AT_MIN_GAP, 3)

    def test_probability_clamped(self):
        """概率始终落在 0.05~0.45 之间"""
        from bot.chat.handler import group_reply_probability
        from bot.chat import handler as H

        for lonely in (0.0, 0.5, 1.0):
            for streak in (0, 2, 5, 20):
                p = group_reply_probability({"lonely": lonely, "mood": 0.0}, streak)
                self.assertGreaterEqual(p, H.GROUP_PROB_MIN)
                self.assertLessEqual(p, H.GROUP_PROB_MAX)

    def test_base_probability(self):
        """没有情绪加成、没有连说时，基础概率是 0.20"""
        from bot.chat.handler import group_reply_probability

        p = group_reply_probability({"lonely": 0.0, "mood": 0.0}, 0)
        self.assertAlmostEqual(p, 0.20, delta=0.001)

    def test_streak_halves(self):
        """连说 3 句没人接，概率减半"""
        from bot.chat.handler import group_reply_probability

        base = group_reply_probability({"lonely": 0.0, "mood": 0.0}, 0)
        decayed = group_reply_probability({"lonely": 0.0, "mood": 0.0}, 3)
        self.assertAlmostEqual(decayed, base * 0.5, delta=0.001)

    def test_cooldown_blocks(self):
        """刚回过（<20 秒）时，没被 @ 一律不接"""
        from bot.chat.handler import should_answer_group, note_group_reply
        from bot.core import state as cfg

        cfg.group_last_reply_ts.clear()
        cfg.group_msg_window.clear()
        note_group_reply(9001)
        ok, why = should_answer_group(9001, False)
        self.assertFalse(ok)
        self.assertIn("冷却", why)
        cfg.group_last_reply_ts.clear()

class TestBaselineMemoryAndCommands(unittest.TestCase):
    """基线：记忆轮数上限与命令可用性"""

    def test_memory_rounds(self):
        """每个对象最多保留 30 轮对话"""
        from bot.core.constants import MAX_USER_ROUND

        self.assertEqual(MAX_USER_ROUND, 30)

    def test_memory_budget(self):
        """分层预算：profile 120 / dialogue 700 / memories 250 / keywords 120 / timeline 200"""
        from bot.memory.inject import BUDGET

        self.assertEqual(BUDGET, {
            "profile": 120,
            "dialogue": 700,
            "memories": 250,
            "keywords": 120,
            "timeline": 200,
        })
        self.assertEqual(sum(BUDGET.values()), 1390, "总预算 1390 字")

    def test_command_count(self):
        """命令数量不少于 26 个（v5 基线）"""
        import bot.commands  # noqa: F401
        from bot.cmd import registry

        self.assertGreaterEqual(len(registry.COMMANDS), 26)

    def test_core_commands_exist(self):
        """核心命令一个都不能少"""
        import bot.commands  # noqa: F401
        from bot.cmd import registry

        for name in ("help", "status", "memory", "diary", "todo",
                     "persona", "stats", "config", "memorybook", "growth"):
            self.assertIn(name, registry.COMMANDS, f"命令 {name} 不见了")

    def test_commands_are_callable(self):
        """每个命令都挂了可调用的 handler"""
        import bot.commands  # noqa: F401
        from bot.cmd import registry

        for name, cmd in registry.COMMANDS.items():
            self.assertTrue(callable(cmd.handler), f"{name} 的 handler 不可调用")

if __name__ == "__main__":
    unittest.main()
