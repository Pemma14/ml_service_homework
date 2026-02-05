from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models import User
from app.routes.dependencies import get_current_user
from app.schemas.transaction_schemas import STransaction, STransactionCreate
from app.services import billing_service

router = APIRouter()

@router.get(
    "/check_balance",
    summary="Баланс пользователя",
    description="Возвращает текущий баланс пользователя в кредитах.",
    response_description="Текущий баланс пользователя"
)
async def get_balance(current_user: User = Depends(get_current_user)):
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
    session: Session = Depends(get_session)
):
    return billing_service.create_replenishment_request(
        session=session,
        user=current_user,
        transaction_data=transaction_data
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
    session: Session = Depends(get_session)
):
    return billing_service.get_transactions_history(session, current_user.id)
