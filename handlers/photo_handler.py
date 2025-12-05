from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes

from utils.ocr import extract_from_receipt
from parser import parse_transaction
from services.db import get_session, Transaction


async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает фото чека.
    """
    file = await update.message.photo[-1].get_file()
    image_bytes = await file.download_as_bytearray()

    await update.message.reply_text("📄 Распознаю чек... Подожди пару секунд ⚙️")

    # --- OCR через DeepSeek ---
    ocr_text = extract_from_receipt(image_bytes)

    if not ocr_text:
        await update.message.reply_text("❌ Не удалось прочитать чек.")
        return

    # --- Пытаемся извлечь сумму/описание через наш общий парсер ---
    parsed = parse_transaction(ocr_text)

    if not parsed:
        await update.message.reply_text(
            f"📝 Чек распознан, но не удалось определить сумму автоматически:\n\n{ocr_text}"
        )
        return

    # --- Сохраняем в БД ---
    session = get_session()

    tx = Transaction(
        user_id=update.message.from_user.id,
        type=parsed["type"],
        amount=parsed["amount"],
        category=parsed["category"],
        description=parsed["description"],
        tx_date=parsed["date"]
    )

    session.add(tx)
    session.commit()
    session.close()

    await update.message.reply_text(
        f"✅ Чек записан!\n"
        f"Сумма: {parsed['amount']:,}\n"
        f"Категория: {parsed['category']}\n"
        f"Тип: {parsed['type']}"
    )


photo_handler = MessageHandler(filters.PHOTO, handle_receipt)
