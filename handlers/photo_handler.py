from telegram.ext import MessageHandler, filters
from utils.ocr import extract_from_image


async def photo_handler(update, context):
    message = update.message
    photo = message.photo[-1]

    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await message.reply_text("📄 Распознаю чек через AI...")

    data = extract_from_image(image_bytes)

    if not data:
        await message.reply_text("❌ Не удалось распознать чек.")
        return

    if not data.get("amount"):
        await message.reply_text("❌ Не получилось определить сумму.")
        return

    # Сохраняем данные до подтверждения
    context.user_data["receipt_data"] = data

    # Передаём на подтверждение
    from handlers.receipt_handler import receipt_handler
    await receipt_handler(update, context)


photo_handler = MessageHandler(filters.PHOTO, photo_handler)
