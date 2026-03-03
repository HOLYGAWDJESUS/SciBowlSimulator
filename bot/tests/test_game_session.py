import unittest
from dataclasses import dataclass
from typing import Any, Dict, Optional

# ✅ Your real import path
from bot.session_manager.game_session import SessionManager
from bot.session_manager.game_session import ChannelDisabledError, NoActiveQuestionError


# Minimal dummy Question object for tests.
# Your SessionManager should only store/return it; it shouldn't require real dataset fields.
@dataclass(frozen=True)
class DummyQuestion:
    tag: str


class FakePicker:
    """
    Deterministic picker that returns questions in a preset order and records calls.
    """
    def __init__(self, questions):
        self._questions = list(questions)
        self.calls = 0
        self.last_criteria: Optional[Dict[str, Any]] = None

    def get_random(self, **criteria):
        self.calls += 1
        self.last_criteria = dict(criteria)
        if not self._questions:
            raise RuntimeError("FakePicker ran out of questions")
        return self._questions.pop(0)


class TestGameSession(unittest.TestCase):
    def setUp(self):
        # fresh manager each test
        self.q1 = DummyQuestion("Q1")
        self.q2 = DummyQuestion("Q2")
        self.picker = FakePicker([self.q1, self.q2])
        self.manager = SessionManager(self.picker)

        # Support either naming style (handle_question/handle_answer OR handle_q/handle_a)
        self.handle_question = (
            getattr(self.manager, "handle_question", None)
            or getattr(self.manager, "handle_q", None)
        )
        self.handle_answer = (
            getattr(self.manager, "handle_answer", None)
            or getattr(self.manager, "handle_a", None)
        )

        if self.handle_question is None:
            self.fail("SessionManager is missing handle_question() / handle_q()")
        if self.handle_answer is None:
            self.fail("SessionManager is missing handle_answer() / handle_a()")

    def test_get_session_creates_new_session(self):
        sess = self.manager.get_session(123)
        self.assertEqual(sess.channel_id, 123)
        self.assertFalse(sess.has_active_question())

    def test_handle_question_picks_new_then_reposts_same(self):
        channel_id = 10

        # First -q should pick a new question and store it
        q = self.handle_question(channel_id, levels=["HS"])
        self.assertEqual(q, self.q1)
        self.assertEqual(self.picker.calls, 1)

        sess = self.manager.get_session(channel_id)
        self.assertTrue(sess.has_active_question())

        # Second -q while active should repost same question (no new pick call)
        q_again = self.handle_question(channel_id, levels=["MS"], subjects=["PHYSICS"])
        self.assertEqual(q_again, self.q1)
        self.assertEqual(self.picker.calls, 1, "Picker should NOT be called again while active")

    def test_active_question_should_not_depend_on_message_id(self):
        """
        Confirms the rule: active question is based on question != None, not message_id.
        """
        channel_id = 20
        q = self.handle_question(channel_id)
        self.assertEqual(q, self.q1)

        sess = self.manager.get_session(channel_id)

        # message_id might still be None, but session is active
        self.assertIsNone(sess.question_message_id)
        self.assertTrue(sess.has_active_question(), "Session should be active even if message_id is None")

        # Another -q should still repost
        q_again = self.handle_question(channel_id)
        self.assertEqual(q_again, self.q1)
        self.assertEqual(self.picker.calls, 1)

    def test_handle_answer_ends_question_immediately(self):
        channel_id = 30

        q = self.handle_question(channel_id)
        self.assertEqual(q, self.q1)

        # First -a ends the question and returns it
        answered = self.handle_answer(channel_id)
        self.assertEqual(answered, self.q1)

        sess = self.manager.get_session(channel_id)
        self.assertFalse(sess.has_active_question(), "Question should be cleared after first -a")

        # Another -a with no active question should error
        with self.assertRaises(NoActiveQuestionError):
            self.handle_answer(channel_id)

        # Now -q should pick a NEW question (q2) because q1 was cleared
        q2 = self.handle_question(channel_id)
        self.assertEqual(q2, self.q2)
        self.assertEqual(self.picker.calls, 2)

    def test_disabled_channel_blocks_actions(self):
        channel_id = 40
        self.manager.disable_channel(channel_id)

        with self.assertRaises(ChannelDisabledError):
            self.handle_question(channel_id)

        with self.assertRaises(ChannelDisabledError):
            self.handle_answer(channel_id)

    def test_enable_disable_idempotent(self):
        channel_id = 50

        # enable even if not disabled should not crash
        self.manager.enable_channel(channel_id)

        self.manager.disable_channel(channel_id)
        self.manager.disable_channel(channel_id)  # disabling twice should not crash

        self.assertFalse(self.manager.is_enabled(channel_id))

        self.manager.enable_channel(channel_id)
        self.manager.enable_channel(channel_id)   # enabling twice should not crash

        self.assertTrue(self.manager.is_enabled(channel_id))


if __name__ == "__main__":
    unittest.main(verbosity=2)