# handlers/receipt_handler.py
import uuid
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from services.save_transaction import save_transaction


# Хранилище временных данных по UID
TEMP_RECEIPTS = {}


# ==========================
#   ПОКАЗ КАРТОЧКИ ПОСЛЕ OCR
# ==========================
async def show_receipt_card(update, context):
    """
    Показывает карточку с данными чека + кнопки.
    Вызывается из photo_handler после OCR.
    """

    data = context.user_data.get("receipt_data")
    message = update.message

    if not data:
        await message.reply_text("❌ Ошибка: данные распознавания не найдены.")
        return

    # Генерируем уникальный ID транзакции
    uid = str(uuid.uuid4())
    TEMP_RECEIPTS[uid] = data

    text = (
        "🧾 *Новая транзакция*\n\n"
        f"💸 *Сумма:* {data['amount']:,} UZS\n"
        f"🏷 *Категория:* {data['category']}\n"
        f"📝 *Описание:* {data['description']}\n"
        f"📅 *Дата:* {data.get('date', '—')}\n\n"
        "Выберите действие:"
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

    await message.reply_markdown(text, reply_markup=keyboard)


# ==========================
#   ОБРАБОТКА КНОПОК
# ==========================
async def receipt_callback(update, context):
    """Обработка кнопок: Одобрить / Отклонить / Изменить."""
    query = update.callback_query
    await query.answer()

    # callback_data = "<action>:<uid>"
    try:
        action, uid = query.data.split(":")
    except:
        await query.edit_message_text("❌ Некорректные данные callback.")
        return

    data = TEMP_RECEIPTS.get(uid)
    if not data:
        await query.edit_message_text("❌ Данные транзакции не найдены (возможно устарели).")
        return

    # ==============
    #  ОДОБРИТЬ
    # ==============
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

        await query.edit_message_text("✅ Транзакция *успешно сохранена!*")
        TEMP_RECEIPTS.pop(uid, None)
        return

    # ==============
    #  ОТКЛОНИТЬ
    # ==============
    elif action == "reject":
        await query.edit_message_text("🚫 Транзакция *отклонена*.")
        TEMP_RECEIPTS.pop(uid, None)
        return

    # ==============
    #  ИЗМЕНИТЬ
    # ==============
    elif action == "edit":
        context.user_data["edit_uid"] = uid
        await query.edit_message_text(
            "✏ *Редактирование*\n\n"
            "Пришлите новую сумму и описание в формате:\n"
            "`50000 такси`\n\n"
            "Или отмените командой /cancel",
            parse_mode="Markdown"
        )
        return


# Регистрируем обработчик
def receipt_handler_register(app):
    app.add_handler(CallbackQueryHandler(receipt_callback))
