from decimal import Decimal
from typing import Any, Dict, Optional, Union

from pydantic import EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.crud import user as user_crud

from app.auth.hash_password import HashPassword
from app.models import MLRequest, User
from app.schemas import SUserRegister, SUserUpdate
from app.utils import (
    UserAlreadyExistsException,
    UserIsNotPresentException,
    IncorrectEmailOrPasswordException,
    transactional,
)


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.hasher = HashPassword()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Получить пользователя по ID.

        Args:
            user_id: ID пользователя

        Returns:
            Объект User или None, если не найден
        """
        return user_crud.get_by_id(self.session, user_id)

    def get_user_by_email(self, email: EmailStr) -> Optional[User]:
        """
        Получить пользователя по email.

        Args:
            email: Email пользователя

        Returns:
            Объект User или None, если не найден
        """
        return user_crud.get_by_email(self.session, email)

    @transactional
    def create_user(self, user_data: Union[SUserRegister, User]) -> User:
        """
        Создать нового пользователя.

        Поддерживает как схему Pydantic, так и готовую модель User (для тестов).

        Args:
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
            if user_crud.get_by_email(self.session, user_data.email):
                raise UserAlreadyExistsException

            # Сохраняем пользователя с хешированным паролем
            user_dict = user_data.model_dump()
            password = user_dict.pop("password")
            user_dict["hashed_password"] = self.hasher.create_hash(password)
            new_user = User(**user_dict)

        user_crud.create(self.session, new_user)
        return new_user

    @transactional
    def delete_user(self, user_id: int) -> bool:
        """
        Удалить пользователя по ID.

        Args:
            user_id: ID пользователя

        Returns:
            True если удаление успешно, False если пользователь не найден
        """
        user = user_crud.get_by_id(self.session, user_id)

        if user:
            user_crud.delete(self.session, user)
            return True
        return False

    @transactional
    def update_user(self, user_id: int, user_update: SUserUpdate) -> User:
        """
        Обновить данные пользователя.

        Args:
            user_id: ID пользователя
            user_update: Данные для обновления

        Returns:
            Обновленный объект User

        Raises:
            UserIsNotPresentException: Если пользователь не найден
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise UserIsNotPresentException

        # Получаем только те поля, которые были явно переданы в запросе
        update_data = user_update.model_dump(exclude_unset=True)

        user_crud.update(self.session, user, update_data)
        return user

    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получить статистику пользователя через SQL агрегацию.

        Args:
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
        result = self.session.execute(query).mappings().one()
        return dict(result)

    def authenticate_user(self, email: EmailStr, password: str) -> User:
        """
        Аутентификация пользователя.

        Args:
            email: Email пользователя
            password: Пароль для проверки

        Returns:
            Объект User при успешной аутентификации

        Raises:
            IncorrectEmailOrPasswordException: Если email или пароль неверны
        """
        user = self.get_user_by_email(email)

        if not user or not self.hasher.verify_hash(password, user.hashed_password):
            raise IncorrectEmailOrPasswordException

        return user


