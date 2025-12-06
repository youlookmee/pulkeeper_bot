import uuid
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters

from utils.ocr import extract_from_image

async def photo_handler(update, context):
    message = update.message
    if not message.photo:
        return

    photo = message.photo[-1]
    await message.reply_text("📄 Распознаю чек через AI...")

    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, extract_from_image, bytes(image_bytes))

    if not data:
        await message.reply_text("❌ Не удалось прочитать чек.")
        return

    uid = str(uuid.uuid4())
    context.user_data[uid] = data

    amt = data["amount"]
    amt_txt = int(amt) if float(amt).is_integer() else amt

    caption = (
        "🧾 *Новая транзакция*\n\n"
        f"💸 *Сумма:* {amt_txt:,} UZS\n"
        f"🏷 *Категория:* {data['category']}\n"
        f"📝 *Описание:* {data['description']}\n"
        f"📅 *Дата:* {data.get('date', '')}\n"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{uid}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{uid}")
        ],
        [InlineKeyboardButton("✏️ Изменить", callback_data=f"edit:{uid}")]
    ])

    # use file_id for sending same image back
    await message.reply_photo(photo=photo.file_id, caption=caption, parse_mode="Markdown", reply_markup=keyboard)

photo_handler = MessageHandler(filters.PHOTO, photo_handler)
