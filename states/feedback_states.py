# states/feedback_states.py (без змін)
from aiogram.fsm.state import StatesGroup, State

class FeedbackStates(StatesGroup):
    # Стейти для вибору типу
    choosing_category = State()
    choosing_anonymity = State()

    # Стейти для надсилання контенту
    waiting_for_news = State()
    waiting_for_ad = State()
    waiting_for_other = State()
    confirming = State()
