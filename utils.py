from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from language import LANG

def lang_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANG["uz"]["uzbek"], callback_data="lang_uz")],
        [InlineKeyboardButton(text=LANG["ru"]["russian"], callback_data="lang_ru")],
    ])
    return kb

def balance_keyboard(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANG[lang]["history_title"], callback_data="history")]
    ])
