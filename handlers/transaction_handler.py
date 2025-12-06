from telegram.ext import MessageHandler, filters
from services.transactions import save_transaction
from utils.parser import parse_transaction_text

async def transaction_handler(update, context):
    text = update.message.text
    parsed = parse_transaction_text(text)
    if not parsed:
        return
    # parsed -> {amount, category, description}
    tx_id = save_transaction(
        update.message.from_user.id,
        parsed["amount"],
        parsed.get("category", "прочее"),
        parsed.get("type", "expense"),
        parsed.get("description", ""),
        parsed.get("date")
    )
    await update.message.reply_text(f"✅ Добавил транзакцию: {parsed['amount']} (id {tx_id})")

transaction_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, transaction_handler)
