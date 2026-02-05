from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.database import get_session
from app.models import User, MLModel
from app.routes.dependencies import get_current_user
from app.schemas.ml_model_schemas import SMLModel
from app.schemas.ml_request_schemas import (
    SMLPredictionRequest,
    SMLPredictionResponse,
    SMLRequestHistory
)
from app.services import ml_request_service
from app.utils import MLRequestNotFoundException

router = APIRouter()

@router.get(
    "/models",
    response_model=List[SMLModel],
    summary="Список доступных моделей",
    description="Возвращает список всех активных ML-моделей в системе.",
    response_description="Список доступных ML-моделей"
)
async def get_models(session: Session = Depends(get_session)):
    query = select(MLModel).where(MLModel.is_active == True)
    result = session.execute(query)
    return result.scalars().all()

@router.post(
    "/predict",
    response_model=SMLPredictionResponse,
    summary="Выполнить предсказание",
    description="Принимает данные, проверяет баланс и возвращает предсказание модели.",
    response_description="Результаты предсказания и стоимость"
)
async def predict(
    request: SMLPredictionRequest,
    model_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    return ml_request_service.predict(
        session=session,
        items=request.data,
        user=current_user,
        model_id=model_id
    )

@router.get(
    "/history",
    response_model=List[SMLRequestHistory],
    summary="История запросов",
    description="Возвращает историю всех ML-запросов текущего пользователя.",
    response_description="История запросов пользователя"
)
async def get_history(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    return ml_request_service.get_all_history(session, current_user.id)

@router.get(
    "/history/{request_id}",
    response_model=SMLRequestHistory,
    summary="Детали запроса",
    description="Возвращает детальную информацию о конкретном ML-запросе.",
    response_description="Детальная информация о запросе"
)
async def get_request_details(
    request_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    request = ml_request_service.get_history_by_id(session, request_id, current_user.id)
    if not request:
        raise MLRequestNotFoundException
    return request
