# handlers/start.py (async db check)

from aiogram import Router, F, Bot   # ← головне — додати Bot сюди
from aiogram.types import Message, CallbackQuery
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from keyboards import get_main_menu_kb
from states.feedback_states import FeedbackStates
from aiogram.fsm.context import FSMContext
from database.db import db

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привіт! 👋\nЦе бот зворотного зв’язку для новинного каналу.\nОбери, що хочеш надіслати:",
        reply_markup=get_main_menu_kb()
    )

@router.message(F.text == "Надіслати новину 📢")
async def start_news(message: Message, state: FSMContext):
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("Зачекай 5 хвилин перед наступним відгуком. Антиспам! 🚫")
        return
    await state.set_state(FeedbackStates.waiting_for_news)
    await message.answer("Опиши новину: текст, фото, відео чи документ. Потім підтверди відправку.", reply_markup=None)

@router.message(F.text == "Запит про рекламу 💼")
async def start_ad(message: Message, state: FSMContext):
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("Зачекай 5 хвилин перед наступним відгуком. Антиспам! 🚫")
        return
    await state.set_state(FeedbackStates.waiting_for_ad)
    await message.answer("Напиши свій запит про рекламу. Можна додати деталі.", reply_markup=None)

@router.message(F.text == "Інше повідомлення ✉️")
async def start_other(message: Message, state: FSMContext):
    if not await db.check_rate_limit(message.from_user.id):
        await message.answer("Зачекай 5 хвилин перед наступним відгуком. Антиспам! 🚫")
        return
    await state.set_state(FeedbackStates.waiting_for_other)
    await message.answer("Напиши своє повідомлення чи питання.", reply_markup=None)
