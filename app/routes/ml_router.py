import logging
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, status

from app.config import settings
from app.models import User
from app.routes.dependencies import get_current_user, get_ml_request_service
from app.schemas.ml_task_schemas import MLResult
from app.schemas.ml_request_schemas import (
    SMLPredictionRequest,
    SMLPredictionResponse,
    SMLRequestHistory
)
from app.services import MLRequestService
from app.services.mltask_client import MLTaskPublisher, RPCPublisher, get_mq_service, get_rpc_client
from app.utils import MLRequestNotFoundException, setup_logging

router = APIRouter()

setup_logging()
logger = logging.getLogger(__name__)

@router.post(
    "/send_task",
    response_model=SMLPredictionResponse,
    summary="Выполнить предсказание",
    description="Отправляет задачу в очередь RabbitMQ и возвращает информацию о запросе.",
    status_code=status.HTTP_202_ACCEPTED
)
async def send_task(
    request: SMLPredictionRequest,
    current_user: User = Depends(get_current_user),
    mq_service: MLTaskPublisher = Depends(get_mq_service),
    ml_service: MLRequestService = Depends(get_ml_request_service)
) -> Dict[str, Any]:
    # Вызываем единый метод ml_request_service
    db_request = await ml_service.create_and_send_task(
        user=current_user,
        input_data=request.data,
        mq_service=mq_service
    )

    # Возвращаем ответ пользователю
    return {
        "request_id": db_request.id,
        "status": db_request.status,
        "message": db_request.message
    }

@router.post(
    "/send_task_rpc",
    summary="Выполнить предсказание (синхронно/RPC)",
    description="Отправляет запрос через RPC и ожидает результат немедленно.",
    status_code=status.HTTP_200_OK
)
async def send_task_rpc(
    request: SMLPredictionRequest,
    current_user: User = Depends(get_current_user),
    rpc_client: RPCPublisher = Depends(get_rpc_client),
    ml_service: MLRequestService = Depends(get_ml_request_service)
) -> Any:
    raw = await ml_service.execute_rpc_predict(
        user=current_user,
        input_data=request.data,
        rpc_client=rpc_client
    )

    # Если пришёл список или скаляр — тоже оборачиваем
    return {"prediction": raw}

@router.post("/results", summary="Сохранить результат", description="Для воркеров")
async def send_task_result(
    result: MLResult,
    ml_service: MLRequestService = Depends(get_ml_request_service)
) -> Dict[str, str]:
    return await ml_service.process_task_result(result)

@router.get(
    "/history",
    response_model=List[SMLRequestHistory],
    summary="История запросов",
    description="Возвращает историю всех ML-запросов текущего пользователя.",
    response_description="История запросов пользователя"
)
async def get_history(
    current_user: User = Depends(get_current_user),
    ml_service: MLRequestService = Depends(get_ml_request_service)
) -> List[SMLRequestHistory]:
    return ml_service.get_all_history(current_user.id)

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
    ml_service: MLRequestService = Depends(get_ml_request_service)
) -> SMLRequestHistory:
    request = ml_service.get_history_by_id(request_id, current_user.id)
    if not request:
        raise MLRequestNotFoundException
    return request
