from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models import TransactionStatus, TransactionType

from app.schemas.base_schema import SBase


class STransactionCreate(SBase):
    amount: float = Field(..., gt=0, description="Сумма пополнения в кредитах")


class STransaction(SBase):
    id: int
    user_id: int
    amount: float
    type: TransactionType
    status: TransactionStatus
    description: Optional[str]
    ml_request_id: Optional[int]
    created_at: datetime
