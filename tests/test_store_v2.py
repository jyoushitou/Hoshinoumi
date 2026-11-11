# ===================== 双读层测试（v17.4） =====================

import json
import sys
import types
import unittest


def _stub_missing_deps():
    def module(name, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    try:
        import pymysql  # noqa: F401
    except ImportError:
        module("pymysql")
        module("pymysql.cursors", DictCursor=object)
        sys.modules["pymysql"].cursors = sys.modules["pymysql.cursors"]
        sys.modules["pymysql"].connect = lambda **kw: None

    for name, attrs in (("jieba", {"lcut": lambda s: list(s)}), ("PIL", {"Image": None})):
        try:
            __import__(name)
        except ImportError:
            module(name, **attrs)


_stub_missing_deps()


class FakeCursor:
    """按 SQL 关键字返回预设数据"""

    def __init__(self, routes):
        self.routes = routes      # [(关键字, rows, fetchone?)]
        self.connection = types.SimpleNamespace(commit=lambda: None)
        self._rows = []
        self._one = None

    def execute(self, sql, args=None):
        low = " ".join(sql.split()).lower()
        self._rows, self._one = [], None
        for key, rows in self.routes.items():
            if key.lower() in low:
                if isinstance(rows, dict):
                    self._one = rows
                else:
                    self._rows = rows
                return 0
        return 0

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._one

    def close(self):
        pass


class TestStoreV2(unittest.TestCase):
    """新表优先、空则回退、字段归一"""

    def _patch(self, routes):
        import botv.infra.conn as conn
        import botv.infra.store_v2 as sv2
        import botv.infra.repo_memory as rm

        cur = FakeCursor(routes)
        orig = (conn.get_cursor, sv2.get_cursor, rm.get_cursor)
        for mod in (conn, sv2, rm):
            mod.get_cursor = lambda: cur
        self.addCleanup(lambda: [setattr(m, "get_cursor", f)
                                 for m, f in zip((conn, sv2, rm), orig)])
        return cur

    def test_memories_from_new_table(self):
        self._patch({"from memories": [
            {"summary": "去打了疫苗", "tags": "生活,健康", "importance": 4,
             "created_at": "2026-11-10"},
        ]})
        from botv.infra.store_v2 import read_memories

        rows = read_memories("1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["summary"], "去打了疫苗")
        self.assertEqual(rows[0]["tags"], ["生活", "健康"])

    def test_memories_fallback_to_events(self):
        self._patch({
            "from memories": [],
            "from events": [{"summary": "旧记忆", "tags": "", "importance": 3,
                             "created_at": None}],
        })
        from botv.infra.store_v2 import read_memories

        rows = read_memories("1")
        self.assertEqual(rows[0]["summary"], "旧记忆")
        self.assertEqual(rows[0]["tags"], [], "空 tags 应归一成空列表")

    def test_state_from_new_table(self):
        self._patch({"from bot_states": {"mood": 0.3, "energy": 0.8, "lonely": 0.1}})
        from botv.infra.store_v2 import read_state

        st = read_state("1")
        self.assertEqual(st["mood"], 0.3)
        self.assertEqual(st["energy"], 0.8)

    def test_state_fallback_to_json(self):
        self._patch({
            "from bot_states": None,
            "kind='state'": {"event_summary": json.dumps({"mood": -0.4, "energy": 0.2})},
        })
        from botv.infra.store_v2 import read_state

        st = read_state("1")
        self.assertEqual(st["mood"], -0.4)

    def test_state_returns_empty_when_nothing(self):
        self._patch({"from bot_states": None, "kind='state'": None})
        from botv.infra.store_v2 import read_state

        self.assertEqual(read_state("1"), {})

    def test_describe(self):
        self._patch({"count(*)": {"n": 7}, "from bot_states": {"1": 1}})
        from botv.infra.store_v2 import describe

        out = describe("1")
        self.assertEqual(out["memories"], 7)


class TestRepoMemoryMerge(unittest.TestCase):
    """旧 JSON 为底 + 新表覆盖"""

    def test_state_merge_keeps_extra_keys(self):
        import botv.infra.repo_memory as R
        import botv.infra.conn as conn

        legacy = json.dumps({"mood": 0.1, "streak": 5, "last": "x"})
        cur = FakeCursor({
            "kind='state'": {"event_summary": legacy},
            "from bot_states": {"mood": 0.6, "energy": 0.9, "lonely": 0.2},
        })
        import botv.infra.store_v2 as sv2

        mods = (conn, sv2, R)
        orig = [m.get_cursor for m in mods]
        for m in mods:
            m.get_cursor = lambda: cur
        try:
            out = json.loads(R.load_state_json("1"))
        finally:
            for m, f in zip(mods, orig):
                m.get_cursor = f

        self.assertEqual(out["mood"], 0.6, "新表应覆盖")
        self.assertEqual(out["streak"], 5, "旧 JSON 独有字段应保留")


if __name__ == "__main__":
    unittest.main()
