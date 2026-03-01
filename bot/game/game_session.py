from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bot.question_base.questions_repo import Question
from bot.question_base.questions_generator import QuestionPicker, NoQuestionsMatchError

# Add server manager ability to disable usage of bot in certain channels e.g. #general
class ChannelDisabledError(Exception):
    pass

# No current questions
class NoActiveQuestionError(Exception):
    pass

@dataclass
class ChannelSession:
    channel_id: int
    question_message_id: int
    question: Question