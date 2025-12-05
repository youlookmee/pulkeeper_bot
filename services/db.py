# finbot/services/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

# Базовый класс для моделей
Base = declarative_base()

# Создаём движок. echo=False — без SQL-логов, future=True — современный режим SQLAlchemy
engine = create_engine(DATABASE_URL, echo=False, future=True)

# Сессии
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def init_db():
    """
    Создаёт таблицы, если их нет. Импортирует models внутри функции,
    чтобы избежать проблем с порядком импорта.
    """
    # Импортируем здесь — чтобы при запуске гарантированно были видны модели
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

def get_session():
    """
    Возвращает новую сессию. Не забывай session.close() после использования.
    """
    return SessionLocal()
