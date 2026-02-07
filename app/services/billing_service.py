from decimal import Decimal
import logging
from datetime import datetime, timezone
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


def create_replenishment_request(
    session: Session,
    user: User,
    transaction_data: STransactionCreate
) -> Transaction:
    """
    Создать запрос на пополнение баланса.

    В DEV режиме транзакция сразу одобряется и баланс обновляется атомарно.
    В PROD режиме создается pending транзакция для последующего одобрения.

    Args:
        session: Сессия БД
        user: Пользователь, пополняющий баланс
        transaction_data: Данные транзакции (сумма)

    Returns:
        Созданная транзакция

    Raises:
        Exception: Если возникла ошибка при работе с БД
    """
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


def get_user_balance(session: Session, user_id: int) -> Decimal:
    """
    Получить актуальный баланс пользователя.

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Баланс пользователя (Decimal)
    """
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()
    return user.balance if user else Decimal("0.0")


def get_transactions_history(session: Session, user_id: int) -> List[Transaction]:
    """
    Получить историю всех транзакций пользователя.

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Список всех транзакций пользователя
    """
    query = select(Transaction).where(Transaction.user_id == user_id)
    result = session.execute(query)
    return result.scalars().all()


def reserve_funds(
    session: Session,
    user: User,
    cost: Decimal,
) -> None:
    """
    Атомарно списывает средства с баланса пользователя.

    Использует атомарный UPDATE с проверкой баланса в WHERE для предотвращения race conditions.

    Args:
        session: Сессия БД
        user: Пользователь
        cost: Сумма к списанию

    Raises:
        InsufficientFundsException: Если средств недостаточно
    """
    result = session.execute(
        update(User)
        .where(User.id == user.id, User.balance >= cost)
        .values(balance=User.balance - cost)
    )

    if result.rowcount == 0:
        logger.error(f"Пользователь {user.id}: Недостаточно средств для списания {cost}")
        raise InsufficientFundsException

    # Фиксируем списание в БД сразу, чтобы другие процессы видели актуальный баланс
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при коммите списания средств: {e}")
        raise


def create_ml_request_history(
    session: Session,
    user: User,
    model_id: int,
    cost: Decimal,
    input_data: list,
    predictions: list = None,
    errors: list = None,
    status: MLRequestStatus = MLRequestStatus.success
) -> MLRequest:
    """
    Создает запись в истории ML-запросов и соответствующую транзакцию оплаты.

    Args:
        session: Сессия БД
        user: Пользователь
        model_id: ID модели
        cost: Стоимость запроса
        input_data: Входные данные
        predictions: Результаты предсказания (опционально)
        errors: Ошибки (опционально)
        status: Статус запроса (по умолчанию success)

    Returns:
        Созданный объект MLRequest

    Raises:
        Exception: Если возникла ошибка при работе с БД
    """
    # 1. Создаем запись в истории ML-запросов
    new_request = MLRequest(
        user_id=user.id,
        model_id=model_id,
        cost=cost,
        input_data=input_data,
        prediction=predictions or [],
        errors=errors or [],
        status=status,
        completed_at=datetime.now(timezone.utc)
    )
    session.add(new_request)
    session.flush()

    # 2. Создаем запись в журнале финансовых транзакций (аудит)
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
        logger.info(f"Запрос №{new_request.id} сохранен в истории для пользователя {user.id}.")
        return new_request
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при сохранении истории запроса: {e}")
        raise


def refund_funds(
    session: Session,
    user: User,
    cost: Decimal,
    reason: str = "Возврат средств"
) -> None:
    """
    Возвращает средства пользователю в случае ошибки.

    Args:
        session: Сессия БД
        user: Пользователь
        cost: Сумма к возврату
        reason: Причина возврата (для аудита)

    Raises:
        Exception: Если возникла ошибка при работе с БД
    """
    session.execute(
        update(User)
        .where(User.id == user.id)
        .values(balance=User.balance + cost)
    )

    # Создаем транзакцию возврата для аудита
    refund_transaction = Transaction(
        user_id=user.id,
        amount=cost,
        type=TransactionType.replenish,
        status=TransactionStatus.approved,
        description=reason
    )
    session.add(refund_transaction)

    try:
        session.commit()
        logger.info(f"Средства {cost} возвращены пользователю {user.id}. Причина: {reason}")
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при выполнении возврата средств: {e}")
        raise
