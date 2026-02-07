from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.hash_password import HashPassword
from app.models import MLRequest, User
from app.schemas import SUserRegister, SUserUpdate
from app.utils import (
    UserAlreadyExistsException,
    UserIsNotPresentException,
    IncorrectEmailOrPasswordException
)

hasher = HashPassword()


def get_all_users(session: Session) -> List[User]:
    """
    Получить всех пользователей.

    Args:
        session: Сессия БД

    Returns:
        Список всех пользователей
    """
    query = select(User)
    result = session.execute(query)
    return result.scalars().all()


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """
    Получить пользователя по ID.

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Объект User или None, если не найден
    """
    query = select(User).where(User.id == user_id)
    result = session.execute(query)
    return result.scalar_one_or_none()


def get_user_by_email(session: Session, email: EmailStr) -> Optional[User]:
    """
    Получить пользователя по email.

    Args:
        session: Сессия БД
        email: Email пользователя

    Returns:
        Объект User или None, если не найден
    """
    query = select(User).where(User.email == email)
    result = session.execute(query)
    return result.scalar_one_or_none()


def create_user(session: Session, user_data: Union[SUserRegister, User]) -> User:
    """
    Создать нового пользователя.

    Поддерживает как схему Pydantic, так и готовую модель User (для тестов).

    Args:
        session: Сессия БД
        user_data: Данные для создания пользователя (схема или модель)

    Returns:
        Созданный объект User

    Raises:
        UserAlreadyExistsException: Если пользователь с таким email уже существует
    """
    if isinstance(user_data, User):  # для тестов
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
        user_dict["hashed_password"] = hasher.create_hash(password)
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
    """
    Удалить пользователя по ID.

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        True если удаление успешно, False если пользователь не найден
    """
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
    """
    Обновить данные пользователя.

    Args:
        session: Сессия БД
        user_id: ID пользователя
        user_update: Данные для обновления

    Returns:
        Обновленный объект User

    Raises:
        UserIsNotPresentException: Если пользователь не найден
    """
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
    """
    Получить статистику пользователя через SQL агрегацию.

    Args:
        session: Сессия БД
        user_id: ID пользователя

    Returns:
        Словарь с количеством запросов (request_count) и общими тратами (total_spent)
    """
    query = (
        select(
            func.count(MLRequest.id).label("request_count"),
            func.coalesce(func.sum(MLRequest.cost), Decimal("0.0")).label("total_spent")
        )
        .where(MLRequest.user_id == user_id)
    )
    result = session.execute(query).mappings().one()
    return dict(result)


def authenticate_user(session: Session, email: EmailStr, password: str) -> User:
    """
    Аутентификация пользователя.

    Args:
        session: Сессия БД
        email: Email пользователя
        password: Пароль для проверки

    Returns:
        Объект User при успешной аутентификации

    Raises:
        IncorrectEmailOrPasswordException: Если email или пароль неверны
    """
    user = get_user_by_email(session, email)

    if not user or not hasher.verify_hash(password, user.hashed_password):
        raise IncorrectEmailOrPasswordException

    return user


