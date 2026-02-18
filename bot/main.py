import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from bot.config import settings
from bot.handlers import router

logger = logging.getLogger(__name__)

async def set_commands(bot: Bot) -> None:
    """Устанавливает список команд для меню бота."""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="login", description="🔐 Войти в систему"),
        BotCommand(command="logout", description="🚪 Выйти из системы"),
        BotCommand(command="me", description="👤 Мой профиль"),
        BotCommand(command="predict", description="🧠 Начать анкетирование"),
        BotCommand(command="balance", description="💰 Проверить баланс"),
        BotCommand(command="history", description="📊 История последних запросов"),
        BotCommand(command="help", description="🆘 Справка"),
    ]
    await bot.set_my_commands(commands)

async def main() -> None:
    # Настройка бота
    bot = Bot(token=settings.bot.TOKEN)
    dp = Dispatcher()

    # Устанавливаем команды в меню
    await set_commands(bot)

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
