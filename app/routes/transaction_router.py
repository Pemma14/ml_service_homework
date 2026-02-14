from typing import List, Dict, Any
from fastapi import APIRouter, Depends

from app.models import User
from app.routes.dependencies import get_current_user, get_billing_service
from app.schemas.transaction_schemas import STransaction, STransactionCreate
from app.services import BillingService

router = APIRouter()

@router.get(
    "/check_balance",
    summary="Баланс пользователя",
    description="Возвращает текущий баланс пользователя в кредитах.",
    response_description="Текущий баланс пользователя"
)
async def get_balance(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return {"balance": current_user.balance}

@router.post(
    "/replenish",
    response_model=STransaction,
    summary="Пополнение баланса",
    description="Создает запрос на пополнение баланса. В режиме DEV баланс пополняется сразу.",
    response_description="Информация о созданной транзакции"
)
async def replenish_balance(
    transaction_data: STransactionCreate,
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
) -> STransaction:
    return billing_service.create_replenishment(
        user=current_user,
        amount=transaction_data.amount
    )

@router.get(
    "/history",
    response_model=List[STransaction],
    summary="История транзакций",
    description="Возвращает историю всех финансовых операций пользователя.",
    response_description="Список транзакций пользователя"
)
async def get_history(
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
) -> List[STransaction]:
    return billing_service.get_transactions_history(current_user.id)

