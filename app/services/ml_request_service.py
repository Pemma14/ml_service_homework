import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.config import settings
from app.models import User, MLRequest, MLModel
from app.schemas import SMLPredictionResponse
from app.ml import ml_engine
from app.services.billing_service import check_balance, process_prediction_payment
from app.utils import MLModelNotFoundException

# Настроим логгер
logger = logging.getLogger(__name__)


def predict(session: Session, items: List[Dict[str, Any]], user: User, model_id: Optional[int] = None) -> SMLPredictionResponse:
    """
    Функция-оркестратор: координирует работу других сервисов.
    """
    logger.info(f"--- Начало обработки запроса для пользователя {user.id} ---")

    # Получаем модель для определения стоимости
    if model_id:
        query = select(MLModel).where(MLModel.id == model_id)
        model = session.execute(query).scalars().first()
        if not model:
            raise MLModelNotFoundException
    else:
        # Если model_id не передан, берем первую активную модель (для упрощения)
        query = select(MLModel).where(MLModel.is_active == True)
        model = session.execute(query).scalars().first()
        if not model:
            raise MLModelNotFoundException
        model_id = model.id

    # Проверка баланса (Billing-сервис)
    total_cost = model.cost
    check_balance(session, user.id, total_cost)
    logger.info(f"Пользователь {user.id}: Баланс подтвержден ({total_cost}). Переходим к валидации данных.")

    # Валидация входных данных (ML-сервис)
    valid_items = ml_engine.validate_features(items)

    # Выполнение предсказания (ML-сервис)
    logger.info(f"Пользователь {user.id}: Запуск ML-модели (LogisticRegression)...")
    predictions = ml_engine.predict(valid_items)
    logger.info(f"Пользователь {user.id}: Предсказание успешно получено.")

    # Списании средств (Billing-сервис)
    process_prediction_payment(
        session=session,
        user=user,
        model_id=model_id,
        cost=total_cost,
        input_data=items,
        predictions=predictions
    )
    logger.info(f"Пользователь {user.id}: Средства списаны.")

    return SMLPredictionResponse(
        predictions=predictions,
        errors=[],
        cost=total_cost
    )


def get_all_history(session: Session, user_id: int) -> List[MLRequest]:
    """Получить историю всех запросов пользователя (сортировка по дате)."""
    query = (
        select(MLRequest)
        .options(joinedload(MLRequest.ml_model))
        .where(MLRequest.user_id == user_id)
        .order_by(MLRequest.created_at.desc())
    )
    result = session.execute(query)
    return result.scalars().all()


def get_history_by_id(session: Session, request_id: int, user_id: int) -> Optional[MLRequest]:
    """Получить конкретный запрос из истории (с данными о модели)."""
    query = (
        select(MLRequest)
        .options(joinedload(MLRequest.ml_model))
        .where(
            MLRequest.id == request_id,
            MLRequest.user_id == user_id
        )
    )
    result = session.execute(query)
    return result.scalar_one_or_none()
