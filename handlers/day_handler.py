# handlers/day_handler.py
import logging
from telegram.ext import CommandHandler
from datetime import datetime
from sqlalchemy import func

# убедись, что эти импорты соответствуют твоей структуре
from services.db import get_session, Transaction

logger = logging.getLogger(__name__)

async def day_report(update, context):
    try:
        user_id = update.effective_user.id
        today = datetime.now().date()

        session = get_session()

        # попробуем аккуратно посчитать суммы (на случай, если поля называются иначе)
        # предполагаем, что модель Transaction имеет: user_id, type (или t_type), amount, tx_date
        # сначала проверим какие атрибуты у Transaction у тебя есть
        # но здесь делаем обычный запрос (подстраховка ниже в Python)
        txs = session.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.tx_date == today
        ).all()

        if not txs:
            await update.message.reply_text("Сегодня записей нет.")
            session.close()
            return

        # Попробуем суммировать надёжно
        income = 0
        expense = 0
        for t in txs:
            # допустимые имена поля типа: 'type' или 't_type'
            tx_type = getattr(t, "type", None)
            if tx_type is None:
                tx_type = getattr(t, "t_type", None)

            amt = getattr(t, "amount", 0) or 0

            if str(tx_type).lower() == "income":
                income += float(amt)
            else:
                # считаем всё остальное расходом
                expense += float(amt)

        balance = income - expense
        msg = (
            "📅 Отчёт за сегодня\n\n"
            f"Доходы: {int(income):,}\n"
            f"Расходы: {int(expense):,}\n"
            f"Чистый баланс: {int(balance):,}\n\n"
            f"Транзакций: {len(txs)}"
        )

        await update.message.reply_text(msg)
        session.close()

    except Exception as e:
        logger.exception("Ошибка в day_report:")
        # отвечаем пользователю дружелюбно, но не делимся трассой
        await update.message.reply_text("Ошибка при формировании отчёта. Посмотри логи в деплое.")
        try:
            session.close()
        except:
            pass

day_handler = CommandHandler("day", day_report)
