from telegram.ext import MessageHandler, filters
from utils.ocr import read_text
from utils.normalizer import normalize_text
from utils.parser_ml import extract_amount, extract_date, extract_name, build_description
from utils.categorizer import categorize
from handlers.transaction_handler import save_transaction


async def receipt_handler(update, context):
    file = await update.message.photo[-1].get_file()
    img = await file.download_as_bytearray()

    await update.message.reply_text("🧾 Распознаю чек...")

    raw = read_text(img)
    text = normalize_text(raw)

    amount = extract_amount(text)
    date = extract_date(text)
    name = extract_name(text)
    category = categorize(text)
    description = build_description(text, name)

    if not amount:
        await update.message.reply_text("❌ Не смог найти сумму в чеке.")
        return

    msg = (
        "📄 *Чек распознан!*\n\n"
        f"💰 Сумма: *{amount:,.0f} сум*\n"
        f"📂 Категория: *{category}*\n"
        f"👤 Имя: *{name or '—'}*\n"
        f"📅 Дата: *{date or '—'}*\n"
        f"📝 Описание: *{description}*\n\n"
        "Подтвердить запись?"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")

    save_transaction(
        user_id=update.effective_user.id,
        amount=amount,
        category=category,
        description=description,
        tx_date=date
    )
