from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.models import Transaction, User, TransactionType, TransactionStatus

def create_transaction(session: Session, transaction: Transaction) -> Transaction:
    """Создать запись в журнале транзакций."""
    session.add(transaction)
    session.flush()
    return transaction

def get_by_user_id(session: Session, user_id: int) -> List[Transaction]:
    """Получить все транзакции пользователя."""
    query = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc())
    result = session.execute(query)
    return list(result.scalars().all())

def get_all(session: Session) -> List[Transaction]:
    """Получить все транзакции в системе (Админ)."""
    query = select(Transaction).order_by(Transaction.created_at.desc())
    result = session.execute(query)
    return list(result.scalars().all())

def get_by_id(session: Session, transaction_id: int) -> Optional[Transaction]:
    """Получить транзакцию по ID."""
    return session.get(Transaction, transaction_id)

def update_user_balance(session: Session, user_id: int, amount: Decimal) -> bool:
    """
    Атомарно обновляет баланс пользователя.
    Для списания amount должен быть отрицательным, для пополнения - положительным.
    При списании проверяет, что баланс >= |amount|.
    """
    if amount < 0:
        # Списание
        result = session.execute(
            update(User)
            .where(User.id == user_id, User.balance >= abs(amount))
            .values(balance=User.balance + amount)
        )
    else:
        # Пополнение
        result = session.execute(
            update(User)
            .where(User.id == user_id)
            .values(balance=User.balance + amount)
        )

    session.flush()
    return result.rowcount > 0


def create_transaction_record(
    session: Session,
    user_id: int,
    amount: Decimal,
    type: TransactionType,
    status: TransactionStatus,
    description: str,
    ml_request_id: Optional[int] = None
) -> Transaction:
    transaction_record = Transaction(
        user_id=user_id,
        amount=amount,
        type=type,
        status=status,
        description=description,
        ml_request_id=ml_request_id
    )
    session.add(transaction_record)
    session.flush()
    return transaction_record
