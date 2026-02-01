from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from abc import abstractmethod
from .base_model import BaseEntity

if TYPE_CHECKING:
    from .user_model import User

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class TransactionType(str, Enum):
    REPLENISH = "replenish"
    PAYMENT = "payment"

@dataclass
class Transaction(BaseEntity):
    user_id: UUID = field(default_factory=uuid4)
    amount: float = 0.0
    status: TransactionStatus = TransactionStatus.PENDING

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError("Сумма транзакции должна быть положительной")

    @abstractmethod
    def apply(self, user: User):
        pass

@dataclass
class Replenishment(Transaction):
    def apply(self, user: User):
        user.wallet.deposit(self.amount)
        self.status = TransactionStatus.COMPLETED

@dataclass
class Payment(Transaction):
    task_id: Optional[UUID] = None
    is_from_hold: bool = False

    def apply(self, user: User):
        try:
            if self.is_from_hold:
                user.wallet.confirm_withdrawal(self.amount)
            else:
                user.wallet.withdraw(self.amount)
            self.status = TransactionStatus.COMPLETED
        except ValueError:
            self.status = TransactionStatus.FAILED
            raise
