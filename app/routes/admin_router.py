from typing import List
from fastapi import APIRouter, Depends

from app.models import User
from app.routes.dependencies import get_current_admin_user, get_admin_service
from app.schemas.user_schemas import SUser, SUserAdminUpdate
from app.schemas.transaction_schemas import STransaction, STransactionCreate
from app.services import AdminService

router = APIRouter()

@router.get(
    "/users",
    response_model=List[SUser],
    summary="Все пользователи (Админ)",
    description="Возвращает список всех пользователей системы. Только для администраторов.",
)
async def read_all_users(
    admin_user: User = Depends(get_current_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
):
    return admin_service.get_all_users()

@router.patch(
    "/users/{user_id}",
    response_model=SUser,
    summary="Обновить пользователя (Админ)",
    description="Администратор может обновить любые данные пользователя, включая баланс и роль.",
)
async def admin_update_user(
    user_id: int,
    user_update: SUserAdminUpdate,
    admin_user: User = Depends(get_current_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> SUser:
    return admin_service.update_user(user_id, user_update)

@router.get(
    "/transactions",
    response_model=List[STransaction],
    summary="Все транзакции системы (Админ)",
    description="Возвращает историю всех транзакций в системе. Только для администраторов.",
)
async def get_all_transactions(
    admin_user: User = Depends(get_current_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> List[STransaction]:
    return admin_service.get_all_transactions()

@router.post(
    "/transactions/replenish/{user_id}",
    response_model=STransaction,
    summary="Прямое пополнение (Админ)",
    description="Администратор напрямую пополняет баланс пользователя.",
)
async def admin_replenish(
    user_id: int,
    transaction_data: STransactionCreate,
    admin_user: User = Depends(get_current_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> STransaction:
    return admin_service.admin_replenish(user_id, transaction_data.amount)

@router.post(
    "/transactions/approve/{transaction_id}",
    response_model=STransaction,
    summary="Одобрение транзакции (Админ)",
    description="Одобрение ожидающей транзакции на пополнение.",
)
async def approve_transaction(
    transaction_id: int,
    admin_user: User = Depends(get_current_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> STransaction:
    return admin_service.approve_transaction(transaction_id)

@router.post(
    "/transactions/reject/{transaction_id}",
    response_model=STransaction,
    summary="Отклонение транзакции (Админ)",
    description="Отклонение ожидающей транзакции на пополнение.",
)
async def reject_transaction(
    transaction_id: int,
    admin_user: User = Depends(get_current_admin_user),
    admin_service: AdminService = Depends(get_admin_service)
) -> STransaction:
    return admin_service.reject_transaction(transaction_id)
