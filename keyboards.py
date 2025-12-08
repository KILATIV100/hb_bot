def get_main_menu_kb() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text="Надіслати новину")],
        [KeyboardButton(text="Запит про рекламу")],
        [KeyboardButton(text="Інше повідомлення")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Відправити", callback_data="confirm_send"),
            InlineKeyboardButton(text="Скасувати", callback_data="cancel_send")
        ]
    ])
