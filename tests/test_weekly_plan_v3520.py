# ===================== v35.2.21.0 周计划表 =====================
import tempfile
import unittest
from pathlib import Path

from bot.life import weekly_plan

SAMPLE = '''<table id="KebiaoTable1"><tr><td>星期\\节次</td><td>一</td></tr>
<tr><td class="left1"><span id="Sjd00">星期一</span></td>
<td><span id="Sjd01"><dl><dt><a>大学物理实验C9903班</a></dt><dd>5106.罗水平</dd><dd>3-5,7(未定)</dd></dl></span></td>
<td><span id="Sjd02"><dl><dt><a>Web系统基础实验（1）1903班</a></dt><dd>4885.杨乐</dd><dd>8-17(惟义楼实验室305)</dd></dl></span></td>
<td></td><td></td><td></td><td></td><td></td></tr>
<tr><td class="left1"><span id="Sjd10">星期二</span></td>
<td><span id="Sjd11"><dl><dt><a>大学英语Ⅲ0203班</a></dt><dd>4930.徐小芳</dd><dd>3-17(5-628（南楼）)</dd></dl></span></td>
<td></td><td></td><td></td><td></td><td></td><td></td></tr></table>'''


class WeeklyPlanTests(unittest.TestCase):
    def test_parse_html(self):
        rows = weekly_plan.parse_html(SAMPLE)
        self.assertEqual(len(rows), 3)
        names = {x["name"] for x in rows}
        self.assertIn("大学物理实验C9903班", names)
        self.assertEqual(rows[0]["weekday"], 1)
        self.assertEqual(rows[0]["weekday_name"], "星期一")
        self.assertEqual(rows[0]["period_start"], 1)
        self.assertEqual(rows[1]["period_start"], 3)

    def test_week_filter_and_storage(self):
        with tempfile.TemporaryDirectory() as td:
            old = weekly_plan.DATA_ROOT
            weekly_plan.DATA_ROOT = Path(td)
            try:
                rows, total = weekly_plan.import_html("u", SAMPLE, 3, dry_run=False)
                self.assertEqual(total, 3)
                self.assertEqual(len(rows), 2)  # 3-5,7 + 3-17
                loaded = weekly_plan.load_week("u", 3)
                self.assertEqual(len(loaded), 2)
            finally:
                weekly_plan.DATA_ROOT = old


if __name__ == "__main__":
    unittest.main()
