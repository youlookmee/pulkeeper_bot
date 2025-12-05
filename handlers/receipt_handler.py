from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from handlers.transaction_handler import save_transaction

# Временное хранилище (если нет Redis)
TEMP_RECEIPTS = {}


async def receipt_handler(update, context):
    """Вызывается после OCR. Показывает кнопки подтверждения."""
    
    message = update.message
    data = context.user_data.get("receipt_data")

    if not data:
        await message.reply_text("❌ Ошибка: данные чека не найдены.")
        return

    # Сохраняем данные в буфер по user_id
    TEMP_RECEIPTS[message.from_user.id] = data

    keyboard = [
        [
            InlineKeyboardButton("✔ Одобрить", callback_data="approve_receipt"),
            InlineKeyboardButton("✖ Отклонить", callback_data="reject_receipt"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🧾 *Новая транзакция*\n\n"
        f"💸 *Сумма:* {data['amount']:,} UZS\n"
        f"🏷 *Категория:* {data['category']}\n"
        f"📝 *Описание:* {data['description']}\n"
        f"📅 *Дата:* {data.get('date', '—')}\n\n"
        "Подтвердить добавление?"
    )

    await message.reply_markdown(text, reply_markup=reply_markup)


async def receipt_callback(update, context):
    """Обрабатывает нажатие кнопок."""
    query = update.callback_query
    user_id = query.from_user.id

    await query.answer()  # Убираем крутилку

    data = TEMP_RECEIPTS.get(user_id)

    if not data:
        await query.edit_message_text("❌ Данные транзакции не найдены.")
        return

    if query.data == "approve_receipt":
        # Сохраняем транзакцию
        save_transaction(
            user_id=user_id,
            data={
                "type": "expense",
                "amount": data["amount"],
                "category": data["category"],
                "description": data["description"],
                "date": data.get("date")
            }
        )
        await query.edit_message_text("✅ Транзакция *успешно добавлена!*")
        TEMP_RECEIPTS.pop(user_id, None)

    elif query.data == "reject_receipt":
        await query.edit_message_text("🚫 Транзакция *отклонена*.")    
        TEMP_RECEIPTS.pop(user_id, None)


def receipt_handler_register(app):
    app.add_handler(CallbackQueryHandler(receipt_callback))
