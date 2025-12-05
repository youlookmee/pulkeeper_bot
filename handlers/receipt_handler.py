from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters

from utils.ocr import ocr_read
from services.db import save_transaction


def parse_ocr_text(text: str):
    """
    Ищем сумму и описание.
    """
    lines = text.splitlines()
    cleaned = [l.strip() for l in lines if l.strip()]

    amount = None
    description = None

    # Простейший парсер сумм
    for l in cleaned:
        if "000" in l or "сум" in l.lower() or "sum" in l.lower():
            digits = "".join([c for c in l if c.isdigit()])
            if digits and len(digits) >= 3:
                amount = int(digits)
                break

    # Описание — первая строка, где нет цифр и не служебная
    for l in cleaned:
        if not any(ch.isdigit() for ch in l) and len(l) > 3:
            description = l
            break

    return amount, description or "Без описания"


async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Основной обработчик фото чека.
    """

    message = update.message
    photo = message.photo[-1]

    # загрузка фото
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await message.reply_text("📄 Распознаю чек...")

    # OCR
    text = ocr_read(image_bytes)

    if not text.strip():
        return await message.reply_text("❌ Не удалось прочитать чек.")

    amount, description = parse_ocr_text(text)

    if not amount:
        return await message.reply_text("❌ Не смог выделить сумму из чека.")

    # красивые кнопки
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve|{amount}|{description}"),
            InlineKeyboardButton("❌ Отклонить", callback_data="reject"),
        ],
        [
            InlineKeyboardButton("✏️ Изменить", callback_data=f"edit|{amount}|{description}")
        ]
    ])

    await message.reply_text(
        f"🧾 *Распознан чек*\n\n"
        f"💸 *Сумма:* {amount:,} UZS\n"
        f"📝 *Описание:* {description}\n\n"
        f"Подтверждаешь?",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ---- CALLBACK HANDLER ----

async def receipt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")

    if data[0] == "reject":
        return await query.edit_message_text("❌ Операция отменена.")

    if data[0] == "approve":
        amount = int(data[1])
        desc = data[2]

        # сохраняем транзакцию
        save_transaction(
            user_id=query.from_user.id,
            data={
                "type": "expense",
                "amount": amount,
                "category": "прочее",
                "description": desc,
                "date": None
            }
        )

        return await query.edit_message_text(
            f"✅ Готово!\nЗаписал расход *{amount:,} сум*.\nОписание: _{desc}_",
            parse_mode="Markdown"
        )

    if data[0] == "edit":
        await query.edit_message_text("✏️ Напиши новую сумму и описание в формате:\n\n`50000 такси`",
                                      parse_mode="Markdown")
