from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.models import User, Transaction, MLRequest


def get_all_users(session: Session) -> List[User]:
    """Получить всех пользователей (Админ)."""
    query = select(User)
    result = session.execute(query)
    return list(result.scalars().all())

def get_all_transactions(session: Session) -> List[Transaction]:
    """Получить все транзакции в системе (Админ)."""
    query = select(Transaction).order_by(Transaction.created_at.desc())
    result = session.execute(query)
    return list(result.scalars().all())

def get_all_requests(session: Session) -> List[MLRequest]:
    """История всех ML-запросов в системе, с подгруженной моделью, по убыванию даты."""
    query = (
        select(MLRequest)
        .options(joinedload(MLRequest.ml_model))
        .order_by(MLRequest.created_at.desc())
    )
    result = session.execute(query)
    return list(result.scalars().all())
