from fastapi import APIRouter
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="Главная страница",
    description="Возвращает приветственное сообщение и список основных возможностей сервиса PsyPharmPredict."
)
async def home_page() -> Dict[str, Any]:
    """Главная страница с описанием сервиса."""
    return {
        "message": "Welcome to PsyPharmPredict.org!",
        "description": "Наш сервис позволяет выполнять предсказания на основе ваших данных. "
                       "Пополняйте баланс и получайте доступ к современным моделям машинного обучения.",
        "features": [
            "Регистрация и личный кабинет",
            "Управление балансом (кредиты)",
            "Предсказание",
            "История запросов и транзакций",
        ]
    }

@router.get(
    "/health",
    response_model=Dict[str, str],
    summary="Проверка работоспособности",
    description="Эндпоинт для мониторинга состояния сервиса. Возвращает статус 'ok', если приложение запущено."
)
async def health_check() -> Dict[str, str]:
    """Проверка работоспособности приложения."""
    logger.info("Эндпоинт health_check успешно вызван")
    return {"status": "ok"}
