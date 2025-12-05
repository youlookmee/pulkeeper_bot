from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes

from utils.ocr import extract_from_receipt
from utils.classify import classify_category, classify_type
from utils.receipt_parser import extract_amount, extract_items
from services.db import get_session, Transaction


async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    img = await file.download_as_bytearray()

    await update.message.reply_text("📄 Распознаю чек...")

    ocr = extract_from_receipt(img)

    if not ocr:
        await update.message.reply_text("❌ Не удалось прочитать чек.")
        return

    raw = ocr.get("raw_text", "")
    total = ocr.get("total") or extract_amount(raw)
    items = ocr.get("items") or extract_items(raw)
    date = ocr.get("date")

    category = classify_category(raw)
    tx_type = classify_type(raw)

    if not total:
        await update.message.reply_text(
            f"Чек распознан, но сумму определить не удалось:\n\n{raw}"
        )
        return

    # ---- сохраняем чек в БД ----
    session = get_session()

    tx = Transaction(
        user_id=update.message.from_user.id,
        type=tx_type,
        amount=total,
        category=category,
        description="Чек: " + (items[0][0] if items else "без позиций"),
        image=img,     # сохраняем фото!
        tx_date=date
    )

    session.add(tx)
    session.commit()
    session.close()

    # ---- создаём красивый ответ ----
    msg = f"✅ Чек записан!\n\n" \
          f"💵 Сумма: {total:,}\n" \
          f"📂 Категория: {category}\n" \
          f"📊 Тип: {tx_type}\n"

    if items:
        msg += "\n🛒 Позиции:\n"
        for name, price in items:
            msg += f"• {name} — {price:,}\n"

    await update.message.reply_text(msg)


photo_handler = MessageHandler(filters.PHOTO, handle_receipt)
