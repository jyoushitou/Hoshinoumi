# ===================== 产物命名（v19.5.7） =====================

import sys
import unittest

sys.path.insert(0, "scripts")

from artifact_names import bundle, checksums, docker, exe, full, src  # noqa: E402


class TestArtifactNames(unittest.TestCase):
    def test_unified_format(self):
        self.assertEqual(src("19.5.7"), "REC-v19.5.7-src.zip")
        self.assertEqual(src("v19.5.7"), "REC-v19.5.7-src.zip")
        self.assertEqual(full("v19.5.7"), "REC-v19.5.7-full.zip")
        self.assertEqual(exe("19.5.7", True), "REC-v19.5.7-exe.exe")
        self.assertEqual(exe("19.5.7", False), "REC-v19.5.7-exe")
        self.assertEqual(docker("19.5.7"), "REC-v19.5.7-docker.tar.gz")
        self.assertEqual(docker("19.5.7", True), "REC-v19.5.7-docker-browser.tar.gz")
        self.assertEqual(bundle("v19.5.7"), "REC-v19.5.7-bundle.bundle")
        self.assertEqual(checksums("19.5.7"), "REC-v19.5.7-SHA256SUMS.txt")

    def test_no_double_v(self):
        self.assertNotIn("vv", src("v19.5.7"))


if __name__ == "__main__":
    unittest.main()
