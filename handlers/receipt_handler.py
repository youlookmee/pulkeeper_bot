# handlers/receipt_handler.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.ocr import extract_from_receipt
from services.db import save_transaction

logger = logging.getLogger(__name__)


async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение фото, OCR → извлечение суммы → вывод карточки подтверждения."""
    message = update.message

    if not message.photo:
        return

    await message.reply_text("📄 Распознаю чек...")

    # выбираем лучшее качество фото
    file_id = message.photo[-1].file_id
    file = await context.bot.get_file(file_id)

    # скачиваем
    img_path = "/tmp/receipt.jpg"
    await file.download_to_drive(img_path)

    # OCR
    try:
        import easyocr
        reader = easyocr.Reader(["ru", "en"], gpu=False)
        ocr_raw = reader.readtext(img_path, detail=0)
        ocr_text = "\n".join(ocr_raw)
    except Exception as e:
        logger.exception(e)
        return await message.reply_text("❌ Не удалось прочитать чек.")

    # анализ
    data = extract_from_receipt(ocr_text)

    amount = data.get("amount")
    merchant = data.get("merchant") or "Неизвестно"
    date = data.get("date") or "Не указана"
    description = data.get("description") or "Без описания"

    if not amount:
        return await message.reply_text("❌ Не получилось определить сумму.")

    # кнопки
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve:{amount}:{merchant}"),
            InlineKeyboardButton("❌ Отклонить", callback_data="decline"),
        ]
    ])

    text = (
        f"Новая транзакция\n"
        f"💸 **Сумма:** {amount} UZS\n"
        f"🏪 **Мерчант:** {merchant}\n"
        f"📅 **Дата:** {date}\n"
        f"📝 **Описание:** {description}"
    )

    await message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def receipt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок Подтвердить / Отклонить."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "decline":
        return await query.edit_message_text("❌ Транзакция отклонена.")

    if data.startswith("approve:"):
        _, amount, merchant = data.split(":")
        save_transaction(
            user_id=query.from_user.id,
            amount=float(amount),
            category="прочее",
            description=f"Чек: {merchant}",
            tx_type="expense",
        )
        return await query.edit_message_text("✅ Транзакция сохранена!")
