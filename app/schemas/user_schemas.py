from decimal import Decimal
from typing import Optional

from pydantic import EmailStr, Field

from app.models.user_model import UserRole
from app.schemas.base_schema import SBase


class SUserRegister(SBase):
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=5, max_length=50, description="Пароль, от 5 до 50 знаков")
    first_name: str = Field(..., min_length=2, max_length=50, description="Имя, от 2 до 50 символов")
    last_name: str = Field(..., min_length=2, max_length=50, description="Фамилия, от 2 до 50 символов")
    phone_number: str = Field(
        ...,
        pattern=r"^\+?[1-9]\d{10,14}$",
        description="Номер телефона в международном формате (например, +79991234567)"
    )


class SUser(SBase):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str
    balance: Decimal
    role: UserRole


class SUserUpdate(SBase):
    first_name: Optional[str] = Field(None, min_length=2, max_length=50, description="Имя")
    last_name: Optional[str] = Field(None, min_length=2, max_length=50, description="Фамилия")
    phone_number: Optional[str] = Field(
        None,
        pattern=r"^\+?[1-9]\d{10,14}$",
        description="Номер телефона"
    )


class SUserAdminUpdate(SUserUpdate):
    balance: Optional[Decimal] = Field(None, ge=0, description="Баланс")
    role: Optional[UserRole] = Field(None, description="Роль пользователя")


class SUserAuth(SBase):
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., description="Пароль")


class SUserWithHistory(SUser):
    # Используем Forward Reference или импорт, если нужно,но пока просто опишем базово, чтобы избежать циклов
    pass
