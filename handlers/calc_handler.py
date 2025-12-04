from telegram.ext import ConversationHandler, MessageHandler, CommandHandler, filters
from telegram import Update
from telegram.ext import ContextTypes

from handlers.common import parse_number
from calculations import compute_financials
from services.chart_service import generate_bar_chart, generate_table_image
from services.deepseek_service import generate_financial_advice

ASK_INCOME, ASK_EXPENSES, ASK_SAVINGS, ASK_LOANS, ASK_ASSETS = range(5)


async def calculate_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Шаг 1/5. Введите ваш ЕЖЕМЕСЯЧНЫЙ доход (пример: 4500):")
    return ASK_INCOME


async def ask_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = parse_number(update.message.text)
    if value is None:
        await update.message.reply_text("Введите число (пример: 4500):")
        return ASK_INCOME

    context.user_data["income"] = value
    await update.message.reply_text("Шаг 2/5. Введите ваши ежемесячные РАСХОДЫ:")
    return ASK_EXPENSES


async def ask_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = parse_number(update.message.text)
    if value is None:
        await update.message.reply_text("Введите число:")
        return ASK_EXPENSES

    context.user_data["expenses"] = value
    await update.message.reply_text("Шаг 3/5. Сколько у вас НАКОПЛЕНО сейчас?")
    return ASK_SAVINGS


async def ask_savings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = parse_number(update.message.text)
    if value is None:
        await update.message.reply_text("Введите число:")
        return ASK_SAVINGS

    context.user_data["savings"] = value
    await update.message.reply_text("Шаг 4/5. Укажите сумму КРЕДИТОВ (если нет — 0):")
    return ASK_LOANS


async def ask_loans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = parse_number(update.message.text)
    if value is None:
        await update.message.reply_text("Введите число:")
        return ASK_LOANS

    context.user_data["loans"] = value
    await update.message.reply_text("Шаг 5/5. Укажите суммарную стоимость АКТИВОВ:")
    return ASK_ASSETS


async def ask_assets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    value = parse_number(update.message.text)
    if value is None:
        await update.message.reply_text("Введите число:")
        return ASK_ASSETS

    # добавляем
    context.user_data["assets"] = value

    # расчёт
    fin = compute_financials(context.user_data)

    # текстовый отчёт
    text_report = (
        "Готово! Вот ваш финансовый отчёт 📊:\n\n"
        f"Доход: {fin['income']}\n"
        f"Расходы: {fin['expenses']}\n"
        f"Net Worth: {fin['net_worth']}\n"
        f"Финансовый балл: {fin['score']} / 100\n"
    )

    await update.message.reply_text(text_report)

    # график
    chart = generate_bar_chart(fin)
    await update.message.reply_photo(chart, caption="📊 График ваших финансов:")

    # таблица
    table_img = generate_table_image(fin)    
    await update.message.reply_photo(table_img, caption="📋 Таблица финансов:")

    # анализ DeepSeek
    advice = generate_financial_advice(fin)
    await update.message.reply_text(advice)

    return ConversationHandler.END


calc_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("calculate", calculate_start)],
    states={
        ASK_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_income)],
        ASK_EXPENSES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_expenses)],
        ASK_SAVINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_savings)],
        ASK_LOANS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_loans)],
        ASK_ASSETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_assets)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: c.user_data.clear())],
)
