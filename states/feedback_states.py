# states/feedback_states.py
from aiogram.fsm.state import StatesGroup, State

class FeedbackStates(StatesGroup):
    # Вибір способу відправки (анонімно чи підписано)
    choosing_anonymity = State()

    # Очікування контенту за типом
    waiting_for_news = State()
    waiting_for_ad = State()
    waiting_for_other = State()

    # Підтвердження перед відправкою
    confirming = State()
