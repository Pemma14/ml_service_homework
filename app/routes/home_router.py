from fastapi import APIRouter, Depends, Response, status
from typing import Any, Dict
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database.database import get_session

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
    description="Эндпоинт для мониторинга состояния сервиса. Проверяет доступность базы данных.",
    responses={
        200: {"description": "Сервис работает нормально"},
        503: {"description": "Сервис недоступен (проблемы с БД)"}
    }
)
async def health_check(response: Response, session: Session = Depends(get_session)) -> Dict[str, str]:
    """Проверка работоспособности приложения и базы данных."""
    try:
        # Выполняем простой запрос для проверки БД
        session.execute(text("SELECT 1"))
        logger.info("Health check passed: database connection is OK")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: database error: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "database": "disconnected", "error": str(e)}
