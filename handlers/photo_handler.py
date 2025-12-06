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
    photo = message.photo[-1]

    await message.reply_text("📄 Распознаю чек через AI...")

    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    # долгое OCR — выносим в executor
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, extract_from_image, bytes(image_bytes))

    if not data:
        await message.reply_text("❌ Не удалось прочитать чек.")
        return

    # Uid для данных
    uid = str(uuid.uuid4())
    context.user_data[uid] = data

    # Текст карточки
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

    await message.reply_photo(
        photo=image_bytes,
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

    raw = query.data.split(":")
    action, uid = raw[0], raw[1]

    data = context.user_data.get(uid)
    if not data:
        await query.edit_message_text("❌ Ошибка: данные не найдены.")
        return

    # ---- ОДОБРИТЬ ----
    if action == "approve":
        save_transaction(
            user_id=query.from_user.id,
            data={
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
            "Отправьте данные в формате:\n"
            "<code>сумма; категория; описание</code>\n\n"
            "Пример:\n<code>7000000; прочее; перевод</code>",
            parse_mode="HTML"
        )
        return


# ===============================================================
# 3) ПОЛЬЗОВАТЕЛЬ ВВОДИТ ИЗМЕНЁННЫЕ ДАННЫЕ
# ===============================================================
async def receipt_edit_message(update, context):
    """Получает сообщение с исправленными данными."""
    uid = context.user_data.get("edit_uid")
    if not uid:
        return

    text = update.message.text.strip()
    parts = [p.strip() for p in text.split(";")]

    if len(parts) != 3:
        await update.message.reply_text("❌ Формат неверный.\nПравильно: 7000000; прочее; перевод")
        return

    amount, category, description = parts

    try:
        amount = float(amount)
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

    # сохраняем в БД
    save_transaction(update.message.from_user.id, data)

    # чистим временные данные
    context.user_data.pop(uid, None)
    context.user_data.pop("edit_uid", None)

    await update.message.reply_text("✅ Транзакция успешно обновлена и сохранена!")


# ===============================================================
# 4) ЭКСПОРТ ХЕНДЛЕРОВ ДЛЯ BOT.PY
# ===============================================================
photo_handler = MessageHandler(filters.PHOTO, photo_handler)
receipt_callback_handler = CallbackQueryHandler(receipt_callback)
receipt_edit_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, receipt_edit_message)
