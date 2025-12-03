FROM python:3.11-slim

WORKDIR /app

# Сначала копируем весь проект
COPY . .

# Теперь ставим зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запуск
CMD ["python", "bot.py"]
