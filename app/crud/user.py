from typing import List, Optional, Any
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import User

def get_all(session: Session) -> List[User]:
    """Получить всех пользователей."""
    query = select(User)
    result = session.execute(query)
    return result.scalars().all()

def get_by_id(session: Session, user_id: int) -> Optional[User]:
    """Получить пользователя по ID."""
    return session.get(User, user_id)

def get_by_email(session: Session, email: EmailStr) -> Optional[User]:
    """Получить пользователя по email."""
    query = select(User).where(User.email == email)
    result = session.execute(query)
    return result.scalar_one_or_none()

def create(session: Session, user: User) -> User:
    """Создать нового пользователя."""
    session.add(user)
    session.flush()
    return user

def delete(session: Session, user: User) -> None:
    """Удалить пользователя."""
    session.delete(user)
    session.flush()

def update(session: Session, user: User, update_data: dict[str, Any]) -> User:
    """Обновить данные пользователя."""
    for key, value in update_data.items():
        setattr(user, key, value)
    session.flush()
    return user
