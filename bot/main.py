import logging
import asyncio
from aiogram import Bot, Dispatcher
from bot.config import settings
from bot.handlers import router

logger = logging.getLogger(__name__)

async def main() -> None:
    # Настройка бота
    bot = Bot(token=settings.bot.TOKEN)
    dp = Dispatcher()

    # Подключаем роутеры с обработчиками
    dp.include_router(router)

    logger.info("Бот запущен...")

    # Запуск polling (опроса серверов Telegram)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    asyncio.run(main())
