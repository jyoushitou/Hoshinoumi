# ===================== v21.9 架构闸门 =====================
import unittest

from scripts.arch_check import check


class TestArchGate(unittest.TestCase):
    def test_no_gate_violations(self):
        result = check()
        self.assertEqual(result["long_functions"], [])
        self.assertEqual(result["events_reads"], [])
        self.assertEqual(result["startup_ddl"], [])
        self.assertEqual(result["persistence_cycle"], [])


if __name__ == "__main__":
    unittest.main()
