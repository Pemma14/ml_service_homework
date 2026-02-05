from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models import MLRequestStatus
from app.schemas.base_schema import SBase
from app.schemas.ml_model_schemas import SMLModel


class SMLPredictionRequest(SBase):
    data: List[Dict[str, Any]] = Field(..., description="Данные для предсказания (список объектов)")


class SMLPredictionResponse(SBase):
    predictions: List[Any] = Field(..., description="Результаты предсказаний для валидных данных")
    errors: List[Dict[str, Any]] = Field(..., description="Ошибочные данные с описанием ошибок")
    cost: float = Field(..., description="Стоимость выполнения запроса")


class SMLRequestHistory(SBase):
    id: int
    user_id: int
    model_id: int
    input_data: List[Dict[str, Any]]
    prediction: Optional[List[Any]]
    errors: Optional[List[Dict[str, Any]]]
    status: MLRequestStatus
    cost: float
    created_at: datetime
    ml_model: Optional[SMLModel] = None
