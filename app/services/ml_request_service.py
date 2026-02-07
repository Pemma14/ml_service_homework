import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.models import User, MLRequest, MLModel
from app.schemas import SMLPredictionResponse
from app.ml import MLEngine
from app.services.billing_service import reserve_funds, create_ml_request_history, refund_funds
from app.utils import MLModelNotFoundException, MLInferenceException


# Настроим логгер
logger = logging.getLogger(__name__)


def predict(
    session: Session,
    items: List[Dict[str, Any]],
    user: User,
    engine: MLEngine,
    model_id: Optional[int] = None
) -> SMLPredictionResponse:
    """
    Функция-оркестратор: координирует работу других сервисов.

    Выполняет полный цикл обработки ML-запроса:
    1. Получает модель и определяет стоимость
    2. Атомарно списывает средства (billing_service)
    3. Выполняет предсказание (ml_engine)
    4. Сохраняет историю запроса
    5. При ошибке возвращает средства

    Args:
        session: Сессия БД
        items: Список входных данных для предсказания
        user: Пользователь
        engine: ML-движок для выполнения предсказаний
        model_id: ID модели (опционально, по умолчанию первая активная)

    Returns:
        Ответ с предсказаниями, ошибками и стоимостью

    Raises:
        MLModelNotFoundException: Если модель не найдена
        InsufficientFundsException: Если недостаточно средств
        MLInferenceException: Если произошла ошибка при инференсе
    """
    logger.info(f"--- Начало обработки запроса для пользователя {user.id} ---")

    # Получаем модель для определения стоимости
    if model_id:
        query = select(MLModel).where(MLModel.id == model_id)
        model = session.execute(query).scalars().first()
        if not model:
            raise MLModelNotFoundException
    else:
        # Если model_id не передан, берем первую активную модель
        query = select(MLModel).where(MLModel.is_active == True)
        model = session.execute(query).scalars().first()
        if not model:
            raise MLModelNotFoundException
        model_id = model.id

    total_cost = model.cost

    # 1. Атомарное списание средств ПЕРЕД инференсом (Billing-сервис)
    # Это предотвращает бесплатную нагрузку на сервер
    reserve_funds(session, user, total_cost)
    logger.info(f"Пользователь {user.id}: Средства {total_cost} успешно зарезервированы.")

    # Подготовка данных для предсказания и сохранения
    prepared_items = []
    for item in items:
        if hasattr(item, "model_dump"):
            prepared_items.append(item.model_dump(by_alias=True))
        else:
            prepared_items.append(item)

    try:
        # 2. Выполнение предсказания (ML-сервис)
        logger.info(f"Пользователь {user.id}: Запуск ML-модели...")
        predictions = engine.predict(prepared_items)
        logger.info(f"Пользователь {user.id}: Предсказание успешно получено.")

        # 3. Сохранение истории (Billing-сервис)
        create_ml_request_history(
            session=session,
            user=user,
            model_id=model_id,
            cost=total_cost,
            input_data=prepared_items,
            predictions=predictions
        )

        return SMLPredictionResponse(
            predictions=predictions,
            errors=[],
            cost=total_cost
        )

    except MLInferenceException as e:
        logger.error(f"Пользователь {user.id}: Ошибка при работе ML-модели. Выполняем возврат средств.")
        refund_funds(session, user, total_cost, reason=f"Ошибка инференса: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Пользователь {user.id}: Непредвиденная ошибка. Выполняем возврат средств.")
        refund_funds(session, user, total_cost, reason=f"Внутренняя ошибка: {str(e)}")
        raise


def get_all_history(session: Session, user_id: int) -> List[MLRequest]:
    """
    Получить историю всех запросов пользователя.

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Список ML-запросов, отсортированный по дате создания (новые первыми)
    """
    query = (
        select(MLRequest)
        .options(joinedload(MLRequest.ml_model))
        .where(MLRequest.user_id == user_id)
        .order_by(MLRequest.created_at.desc())
    )
    result = session.execute(query)
    return result.scalars().all()


def get_history_by_id(session: Session, request_id: int, user_id: int) -> Optional[MLRequest]:
    """
    Получить конкретный запрос из истории.

    Args:
        session: Сессия БД
        request_id: ID запроса
        user_id: ID пользователя (для проверки прав доступа)

    Returns:
        Объект MLRequest или None, если не найден
    """
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
