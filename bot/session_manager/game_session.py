from dataclasses import dataclass
from typing import Optional, Iterable

from bot.question_base.questions_repo import Question
from bot.services.questions_generator import QuestionPicker, NoQuestionsMatchError

# Add server manager ability to disable usage of bot in certain channels e.g. #general
class ChannelDisabledError(Exception):
    pass

# No current questions
class NoActiveQuestionError(Exception):
    pass

@dataclass
class ChannelSession:
    channel_id: int
    message_id: Optional[int] = None
    question: Optional[Question] = None

    # Checks if there is a currently active question
    def has_active_question(self) -> bool:
        return (self.question is not None)
    
    # Mutate channel session

    # Failsafe on whether question is sent before the session is updated.
    def start_question(self, question: Question, question_message_id: Optional[int] = None):
        self.question = question
        self.question_message_id = question_message_id

    def end_question(self):
        self.question = None
        self.question_message_id = None

class SessionManager:

    '''
    Stores that status of all channels
    Chooses question using questions_generator
    '''
    def __init__(self, picker: QuestionPicker):
        self.question_picker = picker
        self.session_library: dict[int, ChannelSession] = {}
        self.disabled_channels: set[int] = set() # saves via channel ID
    
    # Returns status of a channel. If not found (e.g. new channel is made), then stores a new channelsession is channel_id with other categories as blank.
    def get_session(self, channel_id: int) -> ChannelSession:
        if channel_id not in self.session_library:
            self.session_library[channel_id] = ChannelSession(channel_id)
        return self.session_library[channel_id]
    
    # Checks if a channel is enabled via comparing channel id to disabled_channels set
    def is_enabled(self, channel_id: int) -> bool:
        return channel_id not in self.disabled_channels
    
    # Adds channel_id to disabled_channels if not already there
    def disable_channel(self, channel_id: int) -> None:
        if (self.is_enabled(channel_id)):
            self.disabled_channels.add(channel_id)
        else: pass
    
    # Removes channel_id to disabled_channels if already there
    def enable_channel(self, channel_id: int) -> None:
        if (not self.is_enabled(channel_id)):
            self.disabled_channels.discard(channel_id)
        else: pass
    
    # Checks if channel is available for a new question and finds a question based on given criterea
    def handle_question(self, channel_id: int, **criteria) -> Question:
        '''
        If user uses initiates a question, check channel status to decide whether to generate one.
        If channel has active question, return the active question again.
        '''

        # Check if channel is enabled for questions in the first place
        if (not self.is_enabled(channel_id)):
            raise ChannelDisabledError()
        
        status = self.get_session(channel_id)

        # If channel has active question, return active question
        if (status.has_active_question()):
            return status.question
        
        # Tries to find a random question; if none match, raise exception
        # Edits the channel status to use new question
        # Returns new question
        else:
            try:
                new_question = self.question_picker.get_random(**criteria)
                status.start_question(new_question)
                return new_question

            except NoQuestionsMatchError as error:
                raise error
    

    #
    #
    # Add answer judging methods
    #
    #
    # returns the answered_question (to show correct answer later)
    # ends question
    def handle_answer(self, channel_id: int) -> Question:
        """
        Called on -a.
        Ends the active question immediately because first answers changes question regardless if its right or wrong
        and returns the Question to reveal the answer
        """
        if not self.is_enabled(channel_id):
            raise ChannelDisabledError()

        status = self.get_session(channel_id)
        if not status.has_active_question():
            raise NoActiveQuestionError()

        answered_question = status.question
        status.end_question()
        return answered_question
    
    # Method to add message id
    def set_message_id(self, channel_id, message_id):
        status = self.get_session(channel_id)
        if status.has_active_question():
            status.message_id = message_id


            