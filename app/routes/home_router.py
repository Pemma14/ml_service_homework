from fastapi import APIRouter, Depends, Response, status
from typing import Any, Dict
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.database import get_session
from app.services.mltask_client import MLTaskPublisher, get_mq_service

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
    response_model=Dict[str, Any],
    summary="Проверка работоспособности",
    description="Эндпоинт для мониторинга состояния сервиса. Проверяет доступность базы данных и RabbitMQ.",
    responses={
        200: {"description": "Все сервисы работают нормально"},
        503: {"description": "Один или несколько сервисов недоступны"}
    }
)
async def health_check(
    response: Response,
    session: Session = Depends(get_session),
    mq_service: MLTaskPublisher = Depends(get_mq_service)
) -> Dict[str, Any]:
    """Проверка работоспособности приложения, базы данных и RabbitMQ."""
    health_status = {
        "status": "ok",
        "database": "connected",
        "rabbitmq": "connected"
    }

    # 1. Проверка базы данных
    try:
        session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check failed: database error: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "error"
        health_status["database_error"] = str(e)

    # 2. Проверка RabbitMQ
    try:
        async with mq_service.channel_pool.acquire() as channel:
            pass
    except Exception as e:
        logger.error(f"Health check failed: rabbitmq error: {e}")
        health_status["rabbitmq"] = "disconnected"
        health_status["status"] = "error"
        health_status["rabbitmq_error"] = str(e)

    if health_status["status"] == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status
