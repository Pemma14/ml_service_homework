from decimal import Decimal
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import Base, int_pk

if TYPE_CHECKING:
    from app.models import Transaction, User, MLModel


class MLRequestStatus(str, Enum):
    success = "success"
    fail = "fail"
    pending = "pending"


class MLRequest(Base):
    __tablename__ = "ml_request"

    id: Mapped[int_pk]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("ml_model.id"), nullable=False, index=True)
    input_data: Mapped[Any] = mapped_column(JSON, nullable=False)
    prediction: Mapped[Any] = mapped_column(JSON, nullable=True)
    errors: Mapped[Any] = mapped_column(JSON, nullable=True)
    status: Mapped[MLRequestStatus] = mapped_column(nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=text('now()'),
        nullable=False,
        index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Связи с другими таблицами
    user: Mapped["User"] = relationship(back_populates="ml_requests")
    ml_model: Mapped["MLModel"] = relationship(back_populates="ml_requests")
    transaction: Mapped[Optional["Transaction"]] = relationship(
        back_populates="ml_request",
        uselist=False,
    )
