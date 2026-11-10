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


if __name__ == "__main__":
    unittest.main()
