from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models import MLRequestStatus
from app.schemas.base_schema import SBase
from app.schemas.ml_model_schemas import SMLModel


class SMLFeatureItem(SBase):
    age: float = Field(..., alias="Возраст", description="Возраст пациента", ge=0, le=150)
    vnn_pp: int = Field(0, alias="ВНН/ПП", description="ВНН/ПП", ge=0, le=1)
    clozapine: int = Field(0, alias="Клозапин", description="Клозапин", ge=0, le=1)
    cyp2c19_1_2: int = Field(0, alias="CYP2C19 1/2", description="Генетический маркер CYP2C19 1/2", ge=0, le=1)
    cyp2c19_1_17: int = Field(0, alias="CYP2C19 1/17", description="Генетический маркер CYP2C19 1/17", ge=0, le=1)
    cyp2c19_17_17: int = Field(0, alias="CYP2C19 *17/*17", description="Генетический маркер CYP2C19 17/17", ge=0, le=1)
    cyp2d6_1_3: int = Field(0, alias="CYP2D6 1/3", description="Генетический маркер CYP2D6 1/3", ge=0, le=1)

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "Возраст": 35.5,
                "ВНН/ПП": 1,
                "Клозапин": 0,
                "CYP2C19 1/2": 0,
                "CYP2C19 1/17": 1,
                "CYP2C19 *17/*17": 0,
                "CYP2D6 1/3": 0
            }
        }
    }


class SMLPredictionRequest(SBase):
    data: List[SMLFeatureItem] = Field(..., description="Данные для предсказания (список объектов с признаками)", min_length=1, max_length=100)


class SMLPredictionResponse(SBase):
    request_id: int = Field(..., description="ID созданного запроса")
    status: MLRequestStatus = Field(..., description="Текущий статус запроса")
    message: str = Field(..., description="Информационное сообщение")


class SMLRequestHistory(SBase):
    id: int
    user_id: int
    model_id: int
    input_data: List[Dict[str, Any]]
    prediction: Optional[Any] = None
    errors: Optional[List[Dict[str, Any]]]
    status: MLRequestStatus
    cost: Decimal
    created_at: datetime
    ml_model: Optional[SMLModel] = None
