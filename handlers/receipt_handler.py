# handlers/receipt_handler.py
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from services.save_transaction import save_transaction
from services.db import get_user_stats


# ===============================================================
# 1) Универсальная безопасная функция редактирования
# ===============================================================
async def safe_edit(query, text, parse_mode=None):
    """
    Безопасно редактирует сообщение:
    • edit_message_text
    • если сообщение — фото → edit_message_caption
    • если не удалось → отправляет новое сообщение
    """
    try:
        await query.edit_message_text(text, parse_mode=parse_mode)
        return
    except:
        pass

    try:
        await query.edit_message_caption(text, parse_mode=parse_mode)
        return
    except:
        pass

    await query.message.reply_text(text, parse_mode=parse_mode)


# ===============================================================
# 2) ОБРАБОТКА КНОПОК approve / reject / edit
# ===============================================================
async def receipt_callback(update, context):
    """Обрабатывает кнопки Одобрить / Отклонить / Изменить."""
    query = update.callback_query
    await query.answer()

    # Разбираем callback_data
    try:
        action, uid = query.data.split(":")
    except:
        await safe_edit(query, "❌ Ошибка callback.")
        return

    # Достаём данные
    data = context.user_data.get(uid)
    if not data:
        await safe_edit(query, "❌ Данные транзакции устарели или были удалены.")
        return

    # ===============================================================
    # ОДОБРИТЬ ТРАНЗАКЦИЮ
    # ===============================================================
    if action == "approve":

        # сохраняем транзакцию
        save_transaction(
            user_id=query.from_user.id,
            amount=data["amount"],
            category=data["category"],
            tx_type="expense",
            description=data["description"],
            date=data.get("date")
        )

        # удаляем временные данные
        context.user_data.pop(uid, None)

        # получаем статистику пользователя
        stats = get_user_stats(query.from_user.id)

        text = (
            "✅ Обработка завершена\n\n"
            f"💸 Расходы: {stats['expense']:,} UZS\n"
            f"💰 Доходы: {stats['income']:,} UZS\n"
            f"🧾 Транзакции: {stats['count']}\n"
            f"💼 Баланс: {stats['balance']:,} UZS\n\n"
            "💰 *Посмотреть баланс*"
        )

        await safe_edit(query, text, parse_mode="Markdown")
        return

    # ===============================================================
    # ОТКЛОНИТЬ ТРАНЗАКЦИЮ
    # ===============================================================
    if action == "reject":
        context.user_data.pop(uid, None)
        await safe_edit(query, "🚫 Транзакция отменена.")
        return

    # ===============================================================
    # РЕДАКТИРОВАТЬ ТРАНЗАКЦИЮ
    # ===============================================================
    if action == "edit":
        context.user_data["edit_uid"] = uid

        await safe_edit(
            query,
            "✏ <b>Редактирование транзакции</b>\n\n"
            "Введите новую строку в формате:\n"
            "<code>7000000; прочее; перевод</code>",
            parse_mode="HTML"
        )
        return


# ===============================================================
# 3) ПОЛЬЗОВАТЕЛЬ ВВОДИТ ИСПРАВЛЁННЫЕ ДАННЫЕ
# ===============================================================
async def receipt_edit_message(update, context):
    uid = context.user_data.get("edit_uid")
    if not uid:
        return

    text = update.message.text.strip()
    parts = [p.strip() for p in text.split(";")]

    if len(parts) != 3:
        await update.message.reply_text(
            "❌ Неверный формат!\n"
            "Используйте: <code>7000000; прочее; перевод</code>",
            parse_mode="HTML"
        )
        return

    amount_raw, category, description = parts

    # проверяем сумму
    try:
        amount = float(amount_raw)
    except:
        await update.message.reply_text("❌ Ошибка: сумма должна быть числом.")
        return

    data = context.user_data.get(uid)
    if not data:
        await update.message.reply_text("❌ Ошибка: данные не найдены.")
        return

    # обновление данных
    data["amount"] = amount
    data["category"] = category
    data["description"] = description

    # сохраняем
    save_transaction(update.message.from_user.id, data)

    # чистим
    context.user_data.pop(uid, None)
    context.user_data.pop("edit_uid", None)

    await update.message.reply_text("✅ Транзакция обновлена и сохранена!")


# ===============================================================
# 4) РЕГИСТРАЦИЯ ХЕНДЛЕРА
# ===============================================================
def receipt_handler_register(app):
    app.add_handler(CallbackQueryHandler(receipt_callback))
