import logging
import asyncio
from aiogram import Bot, Dispatcher
from app.config import settings
from app.bot.handlers import router

logger = logging.getLogger(__name__)

async def main():
    # Настройка бота
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    # Подключаем роутеры с обработчиками
    dp.include_router(router)

    logger.info("Бот запущен...")

    # Запуск polling (опроса серверов Telegram)
    await dp.start_polling(bot)

if __name__ == "__main__":
    from app.utils import setup_logging
    setup_logging()
    asyncio.run(main())
