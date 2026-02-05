import logging
from datetime import datetime
from typing import List

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    MLRequest,
    MLRequestStatus,
    Transaction,
    TransactionStatus,
    TransactionType,
    User,
)
from app.schemas import STransactionCreate
from app.utils import InsufficientFundsException

logger = logging.getLogger(__name__)


def create_replenishment_request(session: Session, user: User, transaction_data: STransactionCreate) -> Transaction:
    """Создать запрос на пополнение баланса."""
    # В дев режиме (транзакция сразу одобрена)
    if settings.app.MODE == "DEV":
        new_transaction = Transaction(
            user_id=user.id,
            amount=transaction_data.amount,
            type=TransactionType.replenish,
            status=TransactionStatus.approved
        )
        session.add(new_transaction)

        # Атомарно обновляем баланс
        session.execute(
            update(User)
            .where(User.id == user.id)
            .values(balance=User.balance + transaction_data.amount)
        )

        try:
            session.commit()
            session.refresh(new_transaction)
            return new_transaction
        except Exception:
            session.rollback()
            raise

    # В проде
    new_transaction = Transaction(
        user_id=user.id,
        amount=transaction_data.amount,
        type=TransactionType.replenish,
        status=TransactionStatus.pending
    )
    session.add(new_transaction)
    try:
        session.commit()
        session.refresh(new_transaction)
        return new_transaction
    except Exception:
        session.rollback()
        raise


def get_user_balance(session: Session, user_id: int) -> float:
    """Получить актуальный баланс пользователя"""
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()
    return user.balance if user else 0.0


def get_transactions_history(session: Session, user_id: int) -> List[Transaction]:
    """Получить историю всех транзакций пользователя."""
    query = select(Transaction).where(Transaction.user_id == user_id)
    result = session.execute(query)
    return result.scalars().all()


def check_balance(session: Session, user_id: int, cost: float):
    """Проверить, достаточно ли средств у пользователя."""
    balance = get_user_balance(session, user_id)
    if balance < cost:
        logger.error(f"Пользователь {user_id}: Недостаточно средств ({balance} < {cost})")
        raise InsufficientFundsException


def process_prediction_payment(
    session: Session,
    user: User,
    model_id: int,
    cost: float,
    input_data: list,
    predictions: list
) -> MLRequest:
    """
    Атомарная операция: списание средств + запись в историю ML + запись в транзакции.
    Использует атомарный UPDATE для предотвращения race condition.
    """
    # 1. Списываем баланс пользователя атомарно в БД
    result = session.execute(
        update(User)
        .where(User.id == user.id, User.balance >= cost)
        .values(balance=User.balance - cost)
    )

    if result.rowcount == 0:
        logger.error(f"Пользователь {user.id}: Ошибка списания. Недостаточно средств или пользователь не найден.")
        raise InsufficientFundsException

    # 2. Создаем запись в истории ML-запросов
    new_request = MLRequest(
        user_id=user.id,
        model_id=model_id,
        cost=cost,
        input_data=input_data,
        prediction=predictions,
        errors=[],
        status=MLRequestStatus.success,
        completed_at=datetime.now()
    )
    session.add(new_request)

    # Синхронизируем, чтобы получить ID нового запроса
    session.flush()

    # 3. Создаем запись в журнале финансовых транзакций (аудит)
    audit_transaction = Transaction(
        user_id=user.id,
        amount=-cost,
        type=TransactionType.payment,
        status=TransactionStatus.approved,
        description=f"Оплата ML-запроса №{new_request.id}",
        ml_request_id=new_request.id
    )
    session.add(audit_transaction)

    try:
        session.commit()
        session.refresh(new_request)
        logger.info(f"Списано {cost} у пользователя {user.id}. Запрос №{new_request.id} оплачен.")
        return new_request
    except Exception:
        session.rollback()
        raise
