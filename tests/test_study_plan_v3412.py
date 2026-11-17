# ===================== v34.0.1.2 计划视图 =====================
import unittest

from bot.life import study_plan as sp


class TestPlanViewV3412(unittest.TestCase):
    def test_day(self):
        p=sp.empty_week("2026-11-16"); p["monday"]=[{"time":"09:00","task":"x"}]
        self.assertIn("x", sp.format_day(p,"monday"))

    def test_week_empty(self):
        self.assertIn("学习计划", sp.format_week(sp.empty_week("2026-11-16")))


if __name__=="__main__": unittest.main()
