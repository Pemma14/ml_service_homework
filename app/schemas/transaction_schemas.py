from decimal import Decimal
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.models import TransactionStatus, TransactionType

from app.config import settings
from app.schemas.base_schema import SBase


class STransactionCreate(SBase):
    amount: Decimal = Field(
        ...,
        gt=0,
        le=settings.app.MAX_REPLENISH_AMOUNT,
        description=f"Сумма пополнения (от 0.01 до {settings.app.MAX_REPLENISH_AMOUNT} кредитов)"
    )


class STransaction(SBase):
    id: int
    user_id: int
    amount: Decimal
    type: TransactionType
    status: TransactionStatus
    description: Optional[str]
    ml_request_id: Optional[int]
    created_at: datetime
