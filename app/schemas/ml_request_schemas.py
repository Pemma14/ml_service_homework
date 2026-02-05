from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.models import MLRequestStatus
from app.schemas.base_schema import SBase
from app.schemas.ml_model_schemas import SMLModel


class SMLFeatureItem(SBase):
    age: float = Field(..., alias="Возраст", description="Возраст пациента")
    vnn_pp: int = Field(0, alias="ВНН/ПП", description="ВНН/ПП")
    clozapine: int = Field(0, alias="Клозапин", description="Клозапин")
    cyp2c19_1_2: int = Field(0, alias="CYP2C19 1/2", description="Генетический маркер CYP2C19 1/2")
    cyp2c19_1_17: int = Field(0, alias="CYP2C19 1/17", description="Генетический маркер CYP2C19 1/17")
    cyp2c19_17_17: int = Field(0, alias="CYP2C19 *17/*17", description="Генетический маркер CYP2C19 17/17")
    cyp2d6_1_3: int = Field(0, alias="CYP2D6 1/3", description="Генетический маркер CYP2D6 1/3")

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
    data: List[SMLFeatureItem] = Field(..., description="Данные для предсказания (список объектов с признаками)")


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
