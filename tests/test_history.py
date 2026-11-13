# ===================== v19.2 !history =====================
import unittest

from bot.cmd import history_cmd as H
from bot.cmd.registry import CommandContext


class TestHistoryCommand(unittest.TestCase):
    def _ctx(self, parts, uid="1", is_group=False, gid=0):
        return CommandContext(parts=parts, uid=uid, ws=None,
                              is_group=is_group, gid=gid)

    def test_default_and_cap(self):
        self.assertEqual(H._limit(["history"]), 100)
        self.assertEqual(H._limit(["history", "10"]), 10)
        self.assertEqual(H._limit(["history", "999"]), 100)
        self.assertEqual(H._limit(["history", "abc"]), 100)

    def test_format_roles(self):
        text = H._format([
            {"role": "user", "content": "你好", "created_at": "2026-11-13 10:00:00"},
            {"role": "assistant", "content": "嗯", "created_at": "2026-11-13 10:01:00"},
        ])
        self.assertIn("你：你好", text)
        self.assertIn("她：嗯", text)

    def test_empty(self):
        self.assertIn("还没有", H._format([]))

    def test_group_target_and_limit(self):
        seen = {}
        orig = H.repo_conversation if hasattr(H, "repo_conversation") else None
        # import inside command; patch module directly
        from bot.infra import repo_conversation
        old = repo_conversation.recent
        repo_conversation.recent = lambda target, limit=20, **kw: (
            seen.update(target=target, limit=limit) or [])
        try:
            import asyncio
            out = asyncio.run(H.cmd_history(self._ctx(["history", "3"], uid="9", is_group=True, gid=42)))
        finally:
            repo_conversation.recent = old
        self.assertEqual(seen["target"], "42")
        self.assertEqual(seen["limit"], 3)
        self.assertIn("还没有", out)


if __name__ == "__main__":
    unittest.main()
