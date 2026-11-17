# ===================== v34.0.0.1 计划校验 =====================
import unittest
from datetime import date

from bot.life import study_plan as sp


class TestStudyPlanV3401(unittest.TestCase):
    def test_monday(self):
        self.assertEqual(sp.monday_of("2026-11-18"), date(2026,11,16))

    def test_validate(self):
        d=sp.validate_plan({"week_start":"2026-11-18","monday":[{"time":"09:00","task":"x"}]})
        self.assertEqual(d["week_start"],"2026-11-16")
        self.assertEqual(d["monday"][0]["status"],"todo")

    def test_bad_time(self):
        with self.assertRaises(ValueError):
            sp.validate_plan({"week_start":"2026-11-16","monday":[{"time":"25:00"}]})

    def test_roundtrip(self):
        raw={"week_start":"2026-11-16","tuesday":[{"no":1,"time":"10:00","task":"y"}]}
        self.assertEqual(sp.loads(sp.dumps(raw))["tuesday"][0]["task"],"y")


if __name__=="__main__": unittest.main()
