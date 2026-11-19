import base64
import json
import tempfile
import unittest
from pathlib import Path

from bot.infra import image_store


class ImageStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = image_store.BASE
        image_store.BASE = Path(self.tmp.name) / "web_images"

    def tearDown(self):
        image_store.BASE = self.old
        self.tmp.cleanup()

    def test_save_and_attach_data_url(self):
        rel = image_store.save(b"\x89PNG\r\n\x1a\n", "image/png")
        self.assertTrue(rel.startswith("web_images/"))
        item = image_store.attach_image({"meta": json.dumps({"image_path": rel})})
        self.assertTrue(item["image_url"].startswith("data:image/png;base64,"))
        self.assertTrue(base64.b64decode(item["image_url"].split(",", 1)[1]))

    def test_reject_traversal(self):
        self.assertEqual(image_store.to_data_url("../../etc/passwd"), "")

    def test_reject_empty(self):
        self.assertEqual(image_store.save(b"", "image/png"), "")
