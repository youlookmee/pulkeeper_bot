# handlers/photo_handler.py
import uuid
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters
from utils.ocr import extract_from_image


async def photo_handler(update, context):
    """Обрабатывает фото чека — отправляет карточку с кнопками Одобрить/Отклонить/Изменить"""
    message = update.message
    if not message.photo:
        return

    photo = message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await message.reply_text("📄 Распознаю чек через AI...")

    # вызываем OCR (может быть долгим)
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(None, extract_from_image, bytes(image_bytes))

    if not data:
        await message.reply_text("❌ Не удалось прочитать чек.")
        return

     # уникальный ключ для хранения данных в user_data
    uid = str(uuid.uuid4())
    # храним под uid
    context.user_data[uid] = data

    # Формируем текст карточки
    text = (
        "🆕 Новая транзакция\n\n"
        f"💸 Сумма: {int(data['amount']) if float(data['amount']).is_integer() else data['amount']} UZS\n"
        f"📂 Категория: {data.get('category', 'прочее')}\n"
        f"📝 Описание: {data.get('description','')}\n"
        f"📅 Дата: {data.get('date','')}\n"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Одобрить", callback_data=f"approve:{uid}"),
         InlineKeyboardButton("❌ Отклонить", callback_data=f"reject:{uid}")],
        [InlineKeyboardButton("✏️ Изменить", callback_data=f"edit:{uid}")]
    ])

    await message.reply_photo(
        photo=await photo.get_file().download_as_bytearray(),  # просто повторно отправим ту же картинку
        caption=text,
        reply_markup=keyboard
    )

async def receipt_callback(update, context):
    """Обрабатывает кнопки: Одобрить / Отклонить / Изменить"""
    query = update.callback_query
    await query.answer()

    data = context.user_data.get("pending_receipt")

    if not data:
        await query.edit_message_text("❌ Ошибка: данные транзакции не найдены.")
        return

    action = query.data

    # --- ОДОБРЯЕМ ---
    if action == "receipt_approve":
        save_transaction(
            user_id=query.from_user.id,
            data=data
        )
        await query.edit_message_text("✅ Транзакция успешно добавлена!")
        context.user_data.pop("pending_receipt", None)
        return

    # --- ОТКЛОНЯЕМ ---
    elif action == "receipt_decline":
        await query.edit_message_text("❌ Транзакция отменена.")
        context.user_data.pop("pending_receipt", None)
        return

    # --- ИЗМЕНИТЬ ---
    elif action == "receipt_edit":
        context.user_data["edit_mode"] = True

        text = (
            "✏ <b>Редактирование транзакции</b>\n\n"
            "Отправьте данные в формате:\n"
            "<code>сумма; категория; описание</code>\n\n"
            "Например:\n"
            "<code>7000000; прочее; перевод</code>"
        )

        await query.edit_message_text(text, parse_mode="HTML")
        return


async def receipt_edit_message(update, context):
    """Пользователь вручную отправил исправленные данные."""
    if not context.user_data.get("edit_mode"):
        return  # не редактируем

    text = update.message.text
    parts = [p.strip() for p in text.split(";")]

    if len(parts) != 3:
        await update.message.reply_text("❌ Формат неверный. Пример:\n7000000; прочее; перевод")
        return

    amount, category, description = parts
    data = context.user_data.get("pending_receipt")

    # Обновляем данные
    try:
        data["amount"] = float(amount)
        data["category"] = category
        data["description"] = description
    except:
        await update.message.reply_text("❌ Ошибка. Проверьте данные.")
        return

    # Сохраняем
    save_transaction(update.message.from_user.id, data)

    await update.message.reply_text("✅ Транзакция обновлена и сохранена!")

    # очищаем
    context.user_data.pop("edit_mode", None)
    context.user_data.pop("pending_receipt", None)


# Регистрируем хендлеры
photo_handler = MessageHandler(filters.PHOTO, photo_handler)
receipt_callback_handler = CallbackQueryHandler(receipt_callback)
receipt_edit_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), receipt_edit_message)
