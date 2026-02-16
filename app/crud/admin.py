from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import User, Transaction

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
