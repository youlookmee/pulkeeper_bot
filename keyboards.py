from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def draft_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✔ Одобрить", callback_data="draft_accept"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data="draft_decline")
        ],
        [
            InlineKeyboardButton(text="✏ Изменить", callback_data="draft_edit")
        ]
    ])
