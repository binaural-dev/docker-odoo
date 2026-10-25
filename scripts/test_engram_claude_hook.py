"""Unit tests for the SubagentStop capture of the Engram Claude hook (no engram binary needed)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks"))

import engram_claude_hook as hook  # noqa: E402


def event(**overrides):
    base = {
        "hook_event_name": "SubagentStop",
        "session_id": "parent-session",
        "cwd": os.getcwd(),
        "agent_type": "sdd-builder",
        "agent_id": "a1b2c3",
        "last_assistant_message": "Implementado el snapshot con formas sin acentos y tests en verde.",
    }
    base.update(overrides)
    return base


class SubagentObservationTests(unittest.TestCase):
    def test_write_agent_closing_message_is_kept_with_keywords(self):
        topic_key, title, content = hook.subagent_observation(event())
        self.assertEqual(topic_key, "subagente/sdd-builder/a1b2c3")
        self.assertEqual(title, "Cierre de sdd-builder")
        self.assertIn("snapshot", content)
        self.assertIn("keywords:", content)

    def test_every_write_agent_is_captured(self):
        for agent in hook.WRITE_AGENTS:
            self.assertIsNotNone(hook.subagent_observation(event(agent_type=agent)), agent)

    def test_read_only_agents_are_never_captured(self):
        for agent in ("sdd-judge", "sdd-pm", "sdd-qc", "Explore", ""):
            self.assertIsNone(hook.subagent_observation(event(agent_type=agent)), agent)

    def test_secret_is_redacted_before_it_reaches_engram(self):
        _, _, content = hook.subagent_observation(event(last_assistant_message="password: hunter2222 para la base"))
        self.assertNotIn("hunter2222", content)
        self.assertIn("REDACTED", content)

    def test_private_block_is_removed(self):
        _, _, content = hook.subagent_observation(event(last_assistant_message="visible <private>oculto</private> fin"))
        self.assertNotIn("oculto", content)

    def test_message_is_capped_in_bytes(self):
        _, _, content = hook.subagent_observation(event(last_assistant_message="validación " * 1000))
        body = content.split("\nkeywords:")[0]
        self.assertLessEqual(len(body.encode("utf-8")), hook.SUBAGENT_MAX_BYTES)

    def test_empty_message_or_missing_agent_id_returns_none(self):
        self.assertIsNone(hook.subagent_observation(event(last_assistant_message="")))
        self.assertIsNone(hook.subagent_observation(event(last_assistant_message=None)))
        self.assertIsNone(hook.subagent_observation(event(agent_id="")))


if __name__ == "__main__":
    unittest.main()
