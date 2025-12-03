from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# -------------------- LANGUAGE KEYBOARD --------------------
def lang_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O‘zbek", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        ]
    ])
    return kb


# -------------------- BALANCE KEYBOARD --------------------
def balance_keyboard(lang: str):
    if lang == "uz":
        text = {
            "history": "📜 Tarix",
            "stat": "📊 Statistika"
        }
    else:
        text = {
            "history": "📜 История",
            "stat": "📊 Статистика"
        }

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=text["history"], callback_data="history"),
            InlineKeyboardButton(text=text["stat"], callback_data="stat"),
        ]
    ])
    return kb
