from telegram.ext import MessageHandler, filters
from utils.ocr import extract_from_image
from handlers.transaction_handler import save_transaction


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

    # Проверяем сумму
    if not data.get("amount"):
        await message.reply_text("❌ Не получилось определить сумму.")
        return

    # Сохраняем транзакцию
    save_transaction(
        user_id=message.from_user.id,
        data={
            "amount": data["amount"],
            "type": "expense",
            "category": data.get("category", "прочее"),
            "description": data.get("description", "Чек"),
            "date": data.get("date")
        }
    )

    await message.reply_text(
        f"✅ Чек распознан!\n"
        f"Сумма: {data['amount']:,}\n"
        f"Категория: {data['category']}\n"
        f"Описание: {data['description']}\n"
        f"Дата: {data.get('date', '—')}"
    )


photo_handler = MessageHandler(filters.PHOTO, photo_handler)
