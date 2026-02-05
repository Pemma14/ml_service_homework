from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import Base, int_pk

if TYPE_CHECKING:
    from app.models import MLRequest, User


class TransactionStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TransactionType(str, Enum):
    replenish = "replenish"  # Пополнение
    payment = "payment"      # Оплата услуг (списание)


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(nullable=False)
    type: Mapped[TransactionType] = mapped_column(nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        default=TransactionStatus.pending,
        server_default=text("'pending'"),
        nullable=False
    )
    description: Mapped[Optional[str]]
    ml_request_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ml_request.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        server_default=text('now()'),
        nullable=False,
        index=True
    )

    # Связи с другими таблицами
    user: Mapped["User"] = relationship(back_populates="transactions")
    ml_request: Mapped[Optional["MLRequest"]] = relationship(
        back_populates="transaction",
    )
