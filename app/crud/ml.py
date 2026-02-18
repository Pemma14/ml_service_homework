from decimal import Decimal
from typing import List, Optional, Any
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.models import MLModel, MLRequest, MLRequestStatus


def get_active_model(session: Session) -> MLModel:
    """Получить первую активную модель или поднять исключение, если не найдено."""
    query = select(MLModel).where(MLModel.is_active == True)
    model = session.execute(query).scalars().first()
    return model


def list_active_models(session: Session) -> List[MLModel]:
    """Список всех активных моделей."""
    query = select(MLModel).where(MLModel.is_active == True)
    result = session.execute(query)
    return list(result.scalars().all())


def create_request_record(
    session: Session,
    user_id: int,
    model_id: int,
    cost: Decimal,
    input_data: Any,
    status: MLRequestStatus = MLRequestStatus.pending,
) -> MLRequest:
    """Создать запись ML-запроса (без коммита)."""
    new_request = MLRequest(
        user_id=user_id,
        model_id=model_id,
        cost=cost,
        input_data=input_data,
        status=status,
    )
    session.add(new_request)
    session.flush()
    return new_request

def update_request(session: Session, request_id: int, **kwargs: Any) -> Optional[MLRequest]:
    """Обновить поля ML-запроса."""
    db_request = session.get(MLRequest, request_id)
    if db_request:
        for key, value in kwargs.items():
            if hasattr(db_request, key):
                setattr(db_request, key, value)
        session.flush()
    return db_request

def get_history(session: Session, user_id: int) -> List[MLRequest]:
    """История всех запросов пользователя, с подгруженной моделью, по убыванию даты."""
    query = (
        select(MLRequest)
        .options(joinedload(MLRequest.ml_model))
        .where(MLRequest.user_id == user_id)
        .order_by(MLRequest.created_at.desc())
    )
    result = session.execute(query)
    return list(result.scalars().all())


def get_request_by_id(session: Session, request_id: int, user_id: Optional[int] = None) -> Optional[MLRequest]:
    """Получить запрос из истории, опционально проверяя принадлежность пользователю."""
    query = select(MLRequest).options(joinedload(MLRequest.ml_model)).where(MLRequest.id == request_id)
    if user_id is not None:
        query = query.where(MLRequest.user_id == user_id)
    result = session.execute(query)
    return result.scalar_one_or_none()
