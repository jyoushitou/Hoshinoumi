# ===================== v27.2 Manifest / capability / 冲突 =====================
import unittest

from bot.registry import (
    CapabilityUnsupportedError, ManifestError, PluginConflictError,
    PluginManifest, PluginRegistry,
)


def manifest(name="demo", cap="tool.demo@1", priority=0, **kw):
    data = dict(
        name=name, author="author", layer="tools", version="1.0.0",
        api_version=1, requires_core=">=27.0.0", capabilities=(cap,),
        entrypoint="plugin:factory", auto_start=False, priority=priority,
    )
    data.update(kw)
    return PluginManifest(**data)


class TestManifest(unittest.TestCase):
    def test_valid(self):
        m = manifest()
        self.assertIs(m.validate(), m)
        self.assertEqual(m.to_dict()["author"], "author")

    def test_invalid_name_author_layer(self):
        with self.assertRaises(ManifestError):
            manifest(name="Bad Name").validate()
        with self.assertRaises(ManifestError):
            manifest(author="").validate()
        with self.assertRaises(ManifestError):
            manifest(layer="unknown").validate()

    def test_capability_version_2_rejected(self):
        with self.assertRaises(CapabilityUnsupportedError):
            manifest(cap="tool.demo@2").validate()

    def test_api_version_2_rejected(self):
        with self.assertRaises(CapabilityUnsupportedError):
            manifest(api_version=2).validate()

    def test_requires_core(self):
        with self.assertRaises(ManifestError):
            manifest(requires_core=">=99.0.0").validate()
        with self.assertRaises(ManifestError):
            manifest(requires_core="^27.0.0").validate()

    def test_duplicate_capability(self):
        with self.assertRaises(ManifestError):
            manifest(capabilities=("tool.a@1", "tool.a@1")).validate()

    def test_entrypoint(self):
        with self.assertRaises(ManifestError):
            manifest(entrypoint="bad").validate()


class TestRegistryConflicts(unittest.TestCase):
    def setUp(self):
        self.r = PluginRegistry()

    def test_register_manifest(self):
        m = manifest()
        rec = self.r.register_manifest(m, lambda ctx: None)
        self.assertIs(rec.manifest, m)
        self.assertIs(self.r.get("tool.demo@1", "demo"), rec)

    def test_same_name_rejected(self):
        self.r.register_manifest(manifest(), lambda ctx: None)
        with self.assertRaises(PluginConflictError):
            self.r.register_manifest(manifest(), lambda ctx: None)

    def test_same_cap_same_priority_rejected(self):
        self.r.register_manifest(manifest(name="plugina", cap="tool.x@1", priority=0), lambda ctx: None)
        with self.assertRaises(PluginConflictError):
            self.r.register_manifest(manifest(name="pluginb", cap="tool.x@1", priority=0), lambda ctx: None)

    def test_same_cap_higher_priority_allowed(self):
        self.r.register_manifest(manifest(name="plugina", cap="tool.x@1", priority=0), lambda ctx: None)
        self.r.register_manifest(manifest(name="pluginb", cap="tool.x@1", priority=1), lambda ctx: None)
        self.assertEqual(self.r.get("tool.x@1").name, "pluginb")


if __name__ == "__main__":
    unittest.main()


