from __future__ import annotations

import re
from dataclasses import dataclass, field, InitVar
from enum import Enum
from typing import List, TYPE_CHECKING

from .base_model import BaseEntity

if TYPE_CHECKING:
    pass

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

@dataclass
class User(BaseEntity):
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    wallet: Wallet = field(default_factory=lambda: Wallet())
    _history: List[BaseEntity] = field(default_factory=list, repr=False)
    role: UserRole = UserRole.USER
    password: InitVar[str] = ""

    def __post_init__(self, password: str) -> None:
        self._validate_email()
        if password:
            self._validate_password(password)

    def _validate_email(self) -> None:
        email_pattern = re.compile(r"[^@]+@[^@]+\.[^@]+")
        if not email_pattern.match(self.email):
            raise ValueError("Некорректный формат email")

    def _validate_password(self, password: str) -> None:
        if len(password) < 7:
            raise ValueError("Длина пароля не должна быть меньше 7 символов")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or "Anonymous"

    def __repr__(self) -> str:
        return f"User(email='{self.email}', full_name='{self.full_name}', balance={self.balance}, role='{self.role.value}')"

    @property
    def balance(self) -> float:
        return self.wallet.available_balance

    def add_history(self, event: BaseEntity):
        self._history.append(event)

@dataclass
class Wallet:
    _balance: float = 0.0
    _hold_balance: float = 0.0

    @property
    def available_balance(self) -> float:
        return self._balance - self._hold_balance

    @property
    def total_balance(self) -> float:
        return self._balance

    def deposit(self, amount: float):
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        self._balance += amount

    def withdraw(self, amount: float):
        if self.available_balance < amount:
            raise ValueError("Недостаточно средств на балансе")
        self._balance -= amount

    def hold(self, amount: float):
        if self.available_balance < amount:
            raise ValueError("Недостаточно средств для блокировки")
        self._hold_balance += amount

    def release(self, amount: float):
        self._hold_balance = max(0.0, self._hold_balance - amount)

    def confirm_withdrawal(self, amount: float):
        if self._balance < amount:
            raise ValueError("Ошибка подтверждения: сумма больше баланса")
        self._balance -= amount
        self._hold_balance = max(0.0, self._hold_balance - amount)


