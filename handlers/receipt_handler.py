import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from services.transactions import save_transaction

async def safe_edit(query, text, parse_mode=None):
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

async def receipt_callback(update, context):
    query = update.callback_query
    await query.answer()
    try:
        action, uid = query.data.split(":")
    except:
        await safe_edit(query, "❌ Ошибка callback данных.")
        return

    data = context.user_data.get(uid)
    if not data:
        await safe_edit(query, "❌ Данные транзакции устарели.")
        return

    if action == "approve":
        # вызываем синхронную save_transaction в executor
        loop = asyncio.get_running_loop()
        tx_id = await loop.run_in_executor(
            None,
            save_transaction,
            query.from_user.id,
            data["amount"],
            data["category"],
            "expense",
            data["description"],
            data.get("date") or None
        )
        context.user_data.pop(uid, None)
        await safe_edit(query, f"✅ Транзакция сохранена (id: {tx_id})")
        return

    if action == "reject":
        context.user_data.pop(uid, None)
        await safe_edit(query, "🚫 Транзакция отклонена.")
        return

    if action == "edit":
        context.user_data["edit_uid"] = uid
        await safe_edit(query,
            "✏️ Отправьте новую строку в формате:\n<code>7000000; прочее; перевод</code>",
            parse_mode="HTML"
        )
        return

def receipt_callback_handler():
    return CallbackQueryHandler(receipt_callback)
