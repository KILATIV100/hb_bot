# states/feedback_states.py (без змін)
from aiogram.fsm.state import StatesGroup, State

class FeedbackStates(StatesGroup):
    waiting_for_news = State()
    waiting_for_ad = State()
    waiting_for_other = State()
    confirming = State()
