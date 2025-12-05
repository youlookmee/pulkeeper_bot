# handlers/photo_handler.py
from telegram.ext import MessageHandler, filters
from utils.ocr import ocr_read
from parser import parse_transaction
from handlers.transaction_handler import save_transaction


async def photo_handler(update, context):
    """Обрабатывает фото чека"""
    message = update.message

    photo = message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await message.reply_text("📄 Распознаю чек...")

    # OCR (DeepSeek)
    text = ocr_read(image_bytes)

    if not text:
        await message.reply_text("❌ Не удалось прочитать чек.")
        return

    # Парсинг текста чека
    data = parse_transaction(text)

    if not data:
        await message.reply_text("❌ Не получилось определить сумму.")
        return

    # Сохранение транзакции
    save_transaction(message.from_user.id, data)

    await message.reply_text(
        f"✅ Распознано!\n"
        f"Сумма: {data['amount']}\n"
        f"Категория: {data['category']}\n"
        f"Описание: {data['description']}"
    )


photo_handler = MessageHandler(filters.PHOTO, photo_handler)
