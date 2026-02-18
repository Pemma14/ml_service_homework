import logging
from datetime import datetime, timezone
from typing import Any, List, Dict

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import ml as ml_crud
from app.models import User, MLRequest, MLRequestStatus
from app.schemas.ml_task_schemas import MLTask
from app.services.billing_service import BillingService
from app.utils import (
    MLModelNotFoundException,
    MLRequestNotFoundException
)

logger = logging.getLogger(__name__)


def prepare_input_data(input_data: Any) -> Any:
    """
    Преобразует список Pydantic-моделей в список словарей с alias-ключами.
    Возвращает входные данные без изменений, если преобразование не требуется.
    """
    if isinstance(input_data, list) and len(input_data) > 0 and isinstance(input_data[0], BaseModel):
        return [item.model_dump(by_alias=True) for item in input_data]
    return input_data


def build_ml_task(db_request: MLRequest, features: Any, user_id: int) -> MLTask:
    """
    Формирует MLTask на основе записи MLRequest и переданных признаков.
    """
    return MLTask(
        task_id=str(db_request.id),
        features=features,
        model=db_request.ml_model.code_name,
        user_id=user_id,
    )


def create_pending_request(
    session: Session,
    billing_service: BillingService,
    user: User,
    input_data: List[Dict[str, Any]]
) -> MLRequest:
    """
    Создает запрос в статусе ожидания: выбор активной модели, резервирование средств,
    создание записи в БД и запись в аудит.
    """
    logger.info(f"Создание запроса для пользователя {user.id}")

    model = ml_crud.get_active_model(session)
    if not model:
        raise MLModelNotFoundException

    total_cost = settings.app.DEFAULT_REQUEST_COST
    logger.info(f"Стоимость запроса: {total_cost}")

    billing_service.reserve_funds(user, total_cost)

    new_request = ml_crud.create_request_record(
        session=session,
        user_id=user.id,
        model_id=model.id,
        cost=total_cost,
        input_data=input_data,
        status=MLRequestStatus.pending
    )

    billing_service.record_payment_audit(
        user_id=user.id,
        cost=total_cost,
        description=f"Оплата ML-запроса №{new_request.id} (ожидание)",
        ml_request_id=new_request.id
    )

    return new_request


def update_request_result(
    session: Session,
    billing_service: BillingService,
    request_id: int,
    status: MLRequestStatus,
    prediction: Any = None,
    errors: Any = None
) -> MLRequest:
    """
    Обновляет результат запроса в БД. При ошибке выполнения инициирует возврат средств.
    """
    db_request = ml_crud.update_request(
        session,
        request_id,
        status=status,
        prediction=prediction,
        errors=errors,
        completed_at=datetime.now(timezone.utc)
    )

    if not db_request:
        raise MLRequestNotFoundException

    if status == MLRequestStatus.fail:
        user = session.get(User, db_request.user_id)
        if user:
            billing_service.refund_funds(
                user,
                db_request.cost,
                reason=f"Ошибка выполнения запроса №{request_id}"
            )

    return db_request
