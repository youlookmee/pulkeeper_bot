from telegram.ext import CommandHandler
from services.db import get_session, Transaction
from utils.format import money_format


# Иконки категорий (можешь дополнять)
CATEGORY_ICONS = {
    "еда": "🍔",
    "развлечения": "🎉",
    "транспорт": "🚌",
    "прочее": "🔹",
    "зарплата": "💰",
    "покупки": "🛒",
}


def category_icon(cat: str):
    return CATEGORY_ICONS.get(cat.lower(), "🔹")


async def history_command(update, context):
    user_id = update.effective_user.id

    session = get_session()
    rows = (
        session.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.id.desc())
        .limit(10)
        .all()
    )
    session.close()

    if not rows:
        await update.message.reply_text("🕘 История пуста.")
        return

    message = "🧾 *Последние транзакции:*\n\n"

    for tx in rows:
        icon = category_icon(tx.category)
        sign = "➕" if tx.type == "income" else "➖"
        date = tx.tx_date.strftime("%d.%m.%Y")

        message += (
            f"{icon} *{date}*\n"
            f"{sign} {money_format(tx.amount)} — _{tx.category}_\n"
        )

        if tx.description:
            message += f"💬 {tx.description}\n"

        message += "\n"

    await update.message.reply_markdown(message)


def history_handler():
    return CommandHandler("history", history_command)
