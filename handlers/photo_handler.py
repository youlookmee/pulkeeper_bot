# handlers/photo_handler.py
import uuid
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, CallbackQueryHandler, filters

from utils.ocr import extract_from_image
from services.save_transaction import save_transaction


# ===============================================================
# 1) ОБРАБОТКА ФОТО
# ===============================================================
async def photo_handler(update, context):
    """Обрабатывает фото → OCR → карточка с кнопками."""
    message = update.message
    photo = message.photo[-1]  # последнее фото — самое большое

    await message.reply_text("📄 Распознаю чек через AI...")

    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    # OCR — через executor (долго)
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, extract_from_image, bytes(image_bytes))

    if not data:
        await message.reply_text("❌ Не удалось прочитать чек.")
        return

    # UID для временного хранения
    uid = str(uuid.uuid4())
    context.user_data[uid] = data

    amount = data["amount"]
    amount_txt = int(amount) if float(amount).is_integer() else amount

    caption = (
        "🧾 *Новая транзакция*\n\n"
        f"💸 *Сумма:* {amount_txt:,} UZS\n"
        f"🏷 *Категория:* {data['category']}\n"
        f"📝 *Описание:* {data['description']}\n"
        f"📅 *Дата:* {data.get('date', '')}\n"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{uid}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{uid}")
        ],
        [InlineKeyboardButton("✏ Изменить", callback_data=f"edit:{uid}")]
    ])

    # ❗ САМОЕ ВАЖНОЕ — используем file_id, а НЕ bytes.
    await message.reply_photo(
        photo=photo.file_id,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


# ===============================================================
# 2) ОБРАБОТКА КНОПОК
# ===============================================================
async def receipt_callback(update, context):
    """Одобрить / Отклонить / Изменить."""
    query = update.callback_query
    await query.answer()

    try:
        action, uid = query.data.split(":")
    except:
        await query.edit_message_text("❌ Ошибка callback данных.")
        return

    data = context.user_data.get(uid)
    if not data:
        await query.edit_message_text("❌ Данные транзакции устарели.")
        return

    # ---- ОДОБРИТЬ ----
    if action == "approve":
        save_transaction(
            query.from_user.id,
            {
                "type": "expense",
                "amount": data["amount"],
                "category": data["category"],
                "description": data["description"],
                "date": data.get("date")
            }
        )
        context.user_data.pop(uid, None)
        await query.edit_message_text("✅ Транзакция успешно сохранена!")
        return

    # ---- ОТКЛОНИТЬ ----
    elif action == "reject":
        context.user_data.pop(uid, None)
        await query.edit_message_text("🚫 Транзакция отклонена.")
        return

    # ---- ИЗМЕНИТЬ ----
    elif action == "edit":
        context.user_data["edit_uid"] = uid
        await query.edit_message_text(
            "✏ <b>Редактирование</b>\n\n"
            "Введите новые данные в формате:\n"
            "<code>7000000; прочее; перевод</code>",
            parse_mode="HTML"
        )
        return


# ===============================================================
# 3) РЕДАКТИРОВАНИЕ ПОЛЬЗОВАТЕЛЕМ
# ===============================================================
async def receipt_edit_message(update, context):
    uid = context.user_data.get("edit_uid")
    if not uid:
        return  # не в режиме редактирования

    text = update.message.text.strip()
    parts = [p.strip() for p in text.split(";")]

    if len(parts) != 3:
        await update.message.reply_text("❌ Формат неверный.\nПример: 7000000; прочее; перевод")
        return

    amount_raw, category, description = parts

    try:
        amount = float(amount_raw)
    except:
        await update.message.reply_text("❌ Ошибка суммы.")
        return

    data = context.user_data.get(uid)
    if not data:
        await update.message.reply_text("❌ Ошибка данных.")
        return

    # обновляем
    data["amount"] = amount
    data["category"] = category
    data["description"] = description

    # сохраняем
    save_transaction(update.message.from_user.id, data)

    # удаляем временные данные
    context.user_data.pop(uid, None)
    context.user_data.pop("edit_uid", None)

    await update.message.reply_text("✅ Транзакция обновлена и сохранена!")


# ===============================================================
# 4) ЭКСПОРТ ХЕНДЛЕРОВ
# ===============================================================
photo_handler = MessageHandler(filters.PHOTO, photo_handler)
receipt_callback_handler = CallbackQueryHandler(receipt_callback)
receipt_edit_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, receipt_edit_message)
