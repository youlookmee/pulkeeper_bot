# handlers/receipt_handler.py
import asyncio
import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, MessageHandler, filters

from services.save_transaction import save_transaction


# Хранилище данных по UID (если нет Redis)
TEMP_RECEIPTS = {}


# ===============================================================
#   1) ПОКАЗ КАРТОЧКИ ПОСЛЕ OCR  (если надо вызвать отдельно)
# ===============================================================
async def show_receipt_card(update, context):
    """Показывает UI-карточку транзакции (используется при необходимости)."""

    data = context.user_data.get("receipt_data")
    message = update.message

    if not data:
        await message.reply_text("❌ Ошибка: данные чека не найдены.")
        return

    uid = str(uuid.uuid4())
    TEMP_RECEIPTS[uid] = data

    caption = (
        "🧾 *Новая транзакция*\n\n"
        f"💸 *Сумма:* {data['amount']:,} UZS\n"
        f"🏷 *Категория:* {data['category']}\n"
        f"📝 *Описание:* {data['description']}\n"
        f"📅 *Дата:* {data.get('date', '')}\n"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✔ Одобрить", callback_data=f"approve:{uid}"),
            InlineKeyboardButton("✖ Отклонить", callback_data=f"reject:{uid}")
        ],
        [
            InlineKeyboardButton("✏ Изменить", callback_data=f"edit:{uid}")
        ]
    ])

    await message.reply_markdown(caption, reply_markup=keyboard)


# ===============================================================
#   2) ОБРАБОТКА КНОПОК: approve / reject / edit
# ===============================================================
async def receipt_callback(update, context):
    """Обрабатывает кнопки."""
    query = update.callback_query
    await query.answer()

    try:
        action, uid = query.data.split(":")
    except:
        await query.edit_message_text("❌ Ошибка данных кнопки.")
        return

    data = TEMP_RECEIPTS.get(uid)
    if not data:
        await query.edit_message_text("❌ Данные транзакции не найдены.")
        return

    # ✔ ОДОБРЕНИЕ
    if action == "approve":
        loop = asyncio.get_running_loop()

        await loop.run_in_executor(
            None,
            save_transaction,
            query.from_user.id,
            {
                "type": "expense",
                "amount": data["amount"],
                "category": data["category"],
                "description": data["description"],
                "date": data.get("date")
            }
        )

        TEMP_RECEIPTS.pop(uid, None)
        await query.edit_message_text("✅ Транзакция успешно сохранена!")
        return

    # ❌ ОТКЛОНЕНИЕ
    elif action == "reject":
        TEMP_RECEIPTS.pop(uid, None)
        await query.edit_message_text("🚫 Транзакция отклонена.")
        return

    # ✏ РЕДАКТИРОВАНИЕ
    elif action == "edit":
        context.user_data["edit_uid"] = uid

        await query.edit_message_text(
            "✏ <b>Редактирование</b>\n\n"
            "Отправьте исправленные данные в формате:\n"
            "<code>7000000; прочее; перевод</code>",
            parse_mode="HTML"
        )
        return


# ===============================================================
#   3) ПРИЁМ НОВЫХ ДАННЫХ ОТ ПОЛЬЗОВАТЕЛЯ
# ===============================================================
async def receipt_edit_message(update, context):
    """Обрабатывает сообщение вида: 7000000; категория; описание"""

    uid = context.user_data.get("edit_uid")
    if not uid:
        return  # пользователь писал не в режиме редактирования

    text = update.message.text.strip()
    parts = [p.strip() for p in text.split(";")]

    if len(parts) != 3:
        await update.message.reply_text(
            "❌ Неверный формат.\nПример:\n<code>7000000; прочее; перевод</code>",
            parse_mode="HTML"
        )
        return

    amount, category, description = parts

    try:
        amount = float(amount)
    except:
        await update.message.reply_text("❌ Сумма должна быть числом.")
        return

    data = TEMP_RECEIPTS.get(uid)
    if not data:
        await update.message.reply_text("❌ Данные транзакции не найдены.")
        return

    # Обновляем
    data["amount"] = amount
    data["category"] = category
    data["description"] = description

    # Сохраняем
    save_transaction(update.message.from_user.id, data)

    TEMP_RECEIPTS.pop(uid, None)
    context.user_data.pop("edit_uid", None)

    await update.message.reply_text("✅ Транзакция обновлена и сохранена!")


# ===============================================================
#   4) РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ДЛЯ BOT.PY
# ===============================================================
receipt_callback_handler = CallbackQueryHandler(receipt_callback)
receipt_edit_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, receipt_edit_message)
