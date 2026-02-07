from decimal import Decimal
from enum import Enum
from typing import List, TYPE_CHECKING

from sqlalchemy import text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import Base, int_pk, str_uniq

if TYPE_CHECKING:
    from app.models import MLRequest, Transaction


class UserRole(str, Enum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "user"

    id: Mapped[int_pk]
    first_name: Mapped[str]
    last_name: Mapped[str]
    email: Mapped[str_uniq]
    hashed_password: Mapped[str]
    phone_number: Mapped[str_uniq]
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0, server_default=text('0.0'), nullable=False)

    role: Mapped[UserRole] = mapped_column(default=UserRole.user, server_default=text("'user'"), nullable=False)

    # Связи с другими таблицами
    ml_requests: Mapped[List["MLRequest"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def password(self) -> str:
        return self.hashed_password

    @password.setter
    def password(self, value: str):
        self.hashed_password = value
