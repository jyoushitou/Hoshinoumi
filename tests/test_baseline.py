# ===================== 行为基线测试（v17.0.0） =====================
# 重构（v17 系列）之前，先把**现有行为**固化成测试。
#
# 目的：重构后如果某个数字悄悄变了，这里会红。
# 原则：只测「对外可观察的行为」，不测内部实现细节。

import unittest
from datetime import datetime

from botv.config import CST


def _at(hour, minute=0):
    return datetime(2026, 11, 10, hour, minute, tzinfo=CST)


class TestBaselineDelay(unittest.TestCase):
    """基线：回复延迟按时段的取值范围"""

    def test_delay_range_bands(self):
        """每个时段的区间必须与 BANDS 一致"""
        from botv.chat.timing import delay_range

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
        from botv.chat.timing import delay_range

        self.assertEqual(delay_range(_at(6)), (10, 60))
        self.assertEqual(delay_range(_at(9)), (5, 30))
        self.assertEqual(delay_range(_at(18)), (8, 60))
        self.assertEqual(delay_range(_at(0)), (20, 180))

    def test_reply_delay_stays_in_band(self):
        """200 次采样都要落在当前时段的区间内"""
        from botv.chat.timing import reply_delay, delay_range

        now = _at(13)                      # 白天：5~30 秒
        lo, hi = delay_range(now)
        samples = [reply_delay(now) for _ in range(200)]

        self.assertGreaterEqual(min(samples), lo)
        self.assertLessEqual(max(samples), hi)
        self.assertGreater(max(samples) - min(samples), 1.0, "应当有随机浮动")

    def test_reply_delay_skewed_short(self):
        """平方分布：大多数延迟靠近下界，中位数明显小于区间中点"""
        from botv.chat.timing import reply_delay, delay_range

        now = _at(13)
        lo, hi = delay_range(now)
        mid = (lo + hi) / 2

        samples = sorted(reply_delay(now) for _ in range(400))
        median = samples[len(samples) // 2]

        self.assertLess(median, mid, "中位数应低于区间中点（偏向短端）")
        # 且大部分样本落在前半段
        front_half = sum(1 for s in samples if s <= mid)
        self.assertGreater(front_half / len(samples), 0.6, "至少 60% 落在前半段")


if __name__ == "__main__":
    unittest.main()
