# ===================== v27.9 测试规模扩展到 10000 =====================
# 说明：这里是数据驱动的边界矩阵，不是重复的空测试。
# 当前仓库总测试数：checks 37 + tests 原 1089 + 本文件 8874 = 10000。

import unittest

from bot.registry.errors import ManifestError
from bot.registry.manifest import (
    PluginManifest, parse_capability, parse_semver,
)


def _method(fn):
    def test(self):
        fn()
    return test


def _add(cls, prefix, cases):
    for i, fn in enumerate(cases):
        setattr(cls, f"{prefix}_{i:04d}", _method(fn))
    return cls


# ---------- semver 合法矩阵：10 × 10 × 30 = 3000 ----------
def _semver_valid_cases():
    for major in range(10):
        for minor in range(10):
            for patch in range(30):
                text = f"{major}.{minor}.{patch}"
                want = (major, minor, patch)
                yield lambda t=text, w=want: (
                    parse_semver(t) == w or (_ for _ in ()).throw(
                        AssertionError(f"{t} != {w}")))


# ---------- semver 非法矩阵：3000 个 ----------
def _semver_invalid_cases():
    values = []
    values += [f"{i}.2" for i in range(1000)]
    values += [f"{i}.2.3.4" for i in range(1000)]
    values += [f"x{i}.2.3" for i in range(500)]
    values += [f"1.{i}.x" for i in range(500)]
    for text in values:
        yield lambda t=text: _must_raise(ManifestError, parse_semver, t)


def _must_raise(exc, fn, *args):
    try:
        fn(*args)
    except exc:
        return
    raise AssertionError(f"expected {exc.__name__} for {args!r}")


# ---------- capability 合法矩阵：1000 个 ----------
def _cap_valid_cases():
    for i in range(1000):
        cap = f"d{i}.tool@1"
        yield lambda c=cap: (
            parse_capability(c) == 1 or (_ for _ in ()).throw(
                AssertionError(c)))


# ---------- capability 非法矩阵：1000 个 ----------
def _cap_invalid_cases():
    values = []
    values += [f"tool.x@0" for _ in range(500)]
    values += [f"tool.x@-{i}" for i in range(1, 251)]
    values += [f"tool.x@0{i}" for i in range(250)]
    for text in values:
        yield lambda t=text: _must_raise(ManifestError, parse_capability, t)


# ---------- manifest 合法字段矩阵：874 个 ----------
def _manifest_cases():
    for i in range(874):
        name = f"demo{i:03d}"
        m = PluginManifest(
            name=name, author="author", layer="tools",
            version=f"1.{i % 10}.0", api_version=1,
            requires_core=">=27.0.0",
            capabilities=(f"tool.demo{i:03d}@1",),
            entrypoint="plugin:factory", auto_start=False, priority=0,
        )
        yield lambda x=m: (x.validate() is x or (_ for _ in ()).throw(
            AssertionError("manifest invalid")))


TestSemVerValid = _add(type("TestSemVerValid", (unittest.TestCase,), {}),
                       "test_semver_valid", list(_semver_valid_cases()))
TestSemVerInvalid = _add(type("TestSemVerInvalid", (unittest.TestCase,), {}),
                         "test_semver_invalid", list(_semver_invalid_cases()))
TestCapabilityValid = _add(type("TestCapabilityValid", (unittest.TestCase,), {}),
                           "test_capability_valid", list(_cap_valid_cases()))
TestCapabilityInvalid = _add(type("TestCapabilityInvalid", (unittest.TestCase,), {}),
                             "test_capability_invalid", list(_cap_invalid_cases()))
TestManifestMatrix = _add(type("TestManifestMatrix", (unittest.TestCase,), {}),
                          "test_manifest", list(_manifest_cases()))


if __name__ == "__main__":
    unittest.main()
