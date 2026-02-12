from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models import User
from app.routes.dependencies import get_current_user, get_billing_service, get_current_admin_user
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

# === Админские эндпоинты ===

@router.get(
    "/admin/all",
    response_model=List[STransaction],
    summary="Все транзакции системы (Админ)",
    description="Возвращает историю всех транзакций в системе. Только для администраторов.",
)
async def get_all_transactions(
    admin_user: User = Depends(get_current_admin_user),
    billing_service: BillingService = Depends(get_billing_service)
) -> List[STransaction]:
    return billing_service.get_all_transactions()

@router.post(
    "/admin/replenish/{user_id}",
    response_model=STransaction,
    summary="Прямое пополнение (Админ)",
    description="Администратор напрямую пополняет баланс пользователя.",
)
async def admin_replenish(
    user_id: int,
    transaction_data: STransactionCreate,
    admin_user: User = Depends(get_current_admin_user),
    billing_service: BillingService = Depends(get_billing_service)
) -> STransaction:
    return billing_service.admin_replenish(user_id, transaction_data.amount)

@router.post(
    "/admin/approve/{transaction_id}",
    response_model=STransaction,
    summary="Одобрение транзакции (Админ)",
    description="Одобрение ожидающей транзакции на пополнение.",
)
async def approve_transaction(
    transaction_id: int,
    admin_user: User = Depends(get_current_admin_user),
    billing_service: BillingService = Depends(get_billing_service)
) -> STransaction:
    return billing_service.approve_transaction(transaction_id)

@router.post(
    "/admin/reject/{transaction_id}",
    response_model=STransaction,
    summary="Отклонение транзакции (Админ)",
    description="Отклонение ожидающей транзакции на пополнение.",
)
async def reject_transaction(
    transaction_id: int,
    admin_user: User = Depends(get_current_admin_user),
    billing_service: BillingService = Depends(get_billing_service)
) -> STransaction:
    return billing_service.reject_transaction(transaction_id)
