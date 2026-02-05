from typing import Any, Dict, List, Optional, Union

from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MLRequest, User
from app.schemas import SUserRegister, SUserUpdate
from app.utils import (
    UserAlreadyExistsException,
    UserIsNotPresentException,
    IncorrectEmailOrPasswordException
)
from app.utils.auth import get_password_hash, verify_password


def get_all_users(session: Session) -> List[User]:
    """Получить всех пользователей."""
    query = select(User)
    result = session.execute(query)
    return result.scalars().all()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """Получить пользователя по ID."""
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    return result.scalar_one_or_none()


def get_user_by_email(session: Session, email: EmailStr) -> Optional[User]:
    """Получить пользователя по email."""
    query = select(User).where(User.email == email)
    result = session.execute(query)
    return result.scalar_one_or_none()


def create_user(session: Session, user_data: Union[SUserRegister, User]) -> User:
    """Создать нового пользователя. Поддерживает как схему Pydantic, так и готовую модель User."""
    if isinstance(user_data, User): #для тестов
        new_user = user_data
    else:
        # Проверяем, существует ли пользователь
        query = select(User).where(User.email == user_data.email)
        result = session.execute(query)
        if result.scalar_one_or_none():
            raise UserAlreadyExistsException

        # Сохраняем пользователя с хешированным паролем
        user_dict = user_data.model_dump()
        password = user_dict.pop("password")
        user_dict["hashed_password"] = get_password_hash(password)
        new_user = User(**user_dict)

    session.add(new_user)
    try:
        session.commit()
        session.refresh(new_user)
        return new_user
    except Exception:
        session.rollback()
        raise


def delete_user(session: Session, user_id: int) -> bool:
    """Удалить пользователя по ID."""
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    user = result.scalar_one_or_none()

    if user:
        try:
            session.delete(user)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
    return False


def update_user(session: Session, user_id: int, user_update: SUserUpdate) -> User:
    """Обновить данные пользователя."""
    user = get_user_by_id(session, user_id)
    if not user:
        raise UserIsNotPresentException

    # Получаем только те поля, которые были явно переданы в запросе
    update_data = user_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(user, key, value)

    try:
        session.commit()
        session.refresh(user)
        return user
    except Exception:
        session.rollback()
        raise


def get_user_stats(session: Session, user_id: int) -> Dict[str, Any]:
    """Получить статистику пользователя (кол-во запросов и общие траты) через SQL агрегацию."""
    query = (
        select(
            func.count(MLRequest.id).label("request_count"),
            func.coalesce(func.sum(MLRequest.cost), 0.0).label("total_spent")
        )
        .where(MLRequest.user_id == user_id)
    )
    result = session.execute(query).mappings().one()
    return dict(result)


def authenticate_user(session: Session, email: EmailStr, password: str) -> User:
    """Аутентификация пользователя."""
    user = get_user_by_email(session, email)

    if not user or not verify_password(password, user.hashed_password):
        raise IncorrectEmailOrPasswordException

    return user


