# handlers/photo_handler.py
from telegram.ext import MessageHandler, filters, CallbackQueryHandler
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from utils.ocr import extract_from_image
from services.db import save_transaction
import json


async def photo_handler(update, context):
    """Обрабатывает фото чека → OCR → показывает карточку."""
    message = update.message

    photo = message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    await message.reply_text("📄 Распознаю чек через AI...")

    data = extract_from_image(image_bytes)

    if not data:
        await message.reply_text("❌ Не удалось определить данные с чека.")
        return

    # Сохраняем временно результат в context.user_data для callback
    context.user_data["pending_receipt"] = data

    text = (
        "🧾 <b>Новая транзакция</b>\n\n"
        f"💸 <b>Сумма:</b> {int(data['amount']):,} UZS\n"
        f"🏷 <b>Категория:</b> {data['category']}\n"
        f"📝 <b>Описание:</b> {data['description']}\n"
        f"📅 <b>Дата:</b> {data['date'] or '—'}\n"
    ).replace(",", " ")

    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data="receipt_approve"),
            InlineKeyboardButton("❌ Отклонить", callback_data="receipt_decline")
        ],
        [
            InlineKeyboardButton("✏ Изменить", callback_data="receipt_edit")
        ]
    ]

    await message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
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
