import logging

from typing import Generator
from sqlalchemy import create_engine, select, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.models import Base, User
from app.database.seed import seed_db

logger = logging.getLogger(__name__)


# Настройка движка и фабрики сессий
engine_kwargs = settings.db.get_engine_kwargs()
logger.info(f"Подключение к БД (хост: {settings.db.HOST})")

engine: Engine = create_engine(**engine_kwargs)
session_maker = sessionmaker(engine, expire_on_commit=False)


#Геттер для создания движка (будем использовать в инъекциях фастапи)
def get_database_engine() -> Engine:
    return engine

# Генератор сессий (тоже для создания инъекций фастапи)
def get_session() -> Generator[Session, None, None]:
    with session_maker() as session:
        yield session


# Инциализация БД
def init_db(drop_all: bool = False):
    try:
        if drop_all:
            Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        logger.info("Таблицы базы данных успешно инициализированы.")

        # Наполнение начальными данными
        with session_maker() as session:
            # Проверим, есть ли уже пользователи в базе
            user_count = session.execute(select(func.count(User.id))).scalar()
            if user_count == 0:
                logger.info("База данных пуста. Запуск наполнения начальными данными (seed)...")
                seed_db(session)
            else:
                logger.info(f"В базе уже есть данные ({user_count} пользователей). Пропуск сидинга.")

    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise
