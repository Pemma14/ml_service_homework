from __future__ import annotations

from dataclasses import dataclass, field, InitVar
from enum import Enum
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
from abc import ABC, abstractmethod
from uuid import UUID, uuid4

from lesson_1.auth_helper import PasswordHash, PasswordHasher


#Базовые сущности (Models)

# 0. Базовый абстрактный класс для всех сущностей.

@dataclass
class BaseEntity(ABC):
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)


# 1. Пользователь

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


@dataclass
class User(BaseEntity):
    email: str = ""  # аргумент по умолчанию, чтобы питон не ругался, проверка внизу не допустит пустого поля
    _hashed_password: Optional[PasswordHash] = field(default=None, repr=False)
    first_name: str = ""
    last_name: str = ""
    wallet: Wallet = field(default_factory=lambda: Wallet())
    _history: List[BaseEntity] = field(default_factory=list, repr=False)
    role: UserRole = UserRole.USER
    password: InitVar[str] = ""

    def __post_init__(self, password: str) -> None:
        self._validate_email()
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


# 2. Запрос

class RequestStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "pending"
    SUCCESS = "success"
    ERROR = "fail"


@dataclass
class MLRequest(BaseEntity):
    user_id: UUID = field(default_factory=uuid4)
    input_data: Dict[str, Any] = field(default_factory=dict)
    prediction: Optional[Any] = None
    status: RequestStatus = RequestStatus.CREATED
    cost: float = 10.0
    error_message: Optional[str] = None

    def complete(self, result: Any):
        self.prediction = result
        self.status = RequestStatus.SUCCESS

    def fail(self, message: str):
        self.status = RequestStatus.ERROR
        self.error_message = message


# 3. Транзакция

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


# Сервисы

class UserService:
    def __init__(self, hasher: PasswordHasher):
        self._hasher = hasher

    def register_user(self, email: str, password: str, first_name: str = "", last_name: str = "") -> User:
        # Сначала проверяем, существует ли пользователь в бд (когда подключим её)
        # Хешируем и сохраняем пароль
        hashed = self._hasher.hash_password(password)
        return User(
            email=email,
            password=password,
            _hashed_password=hashed,
            first_name=first_name,
            last_name=last_name
        )

    def authenticate_user(self, email: str, password: str) -> User:
        # Поиск пользователя в базе данных (когда подключим её)
        # Проверка через что пароль пользователя соотвествует хешированному
        user = None  # заглушка

        if user and self.verify_user(user, password):
            return user

        raise ValueError("Неверный email или пароль")

    def verify_user(self, user: User, password: str) -> bool:
        if not user._hashed_password:
            return False
        return self._hasher.verify_password(password, user._hashed_password)


class BillingService:
    def hold_funds(self, user: User, amount: float):
        user.wallet.hold(amount)

    def void_hold(self, user: User, amount: float):
        user.wallet.release(amount)

    def replenish(self, user: User, amount: float) -> Replenishment:
        topup = Replenishment(user_id=user.id, amount=amount)
        topup.apply(user)
        user.add_history(topup)
        return topup

    def create_payment(self, user: User, amount: float, task_id: UUID, from_hold: bool = False) -> Payment:
        payment = Payment(user_id=user.id, amount=amount, task_id=task_id, is_from_hold=from_hold)
        payment.apply(user)
        user.add_history(payment)
        return payment


class MLEngine(ABC):
    def __init__(self):
        self.model = None  # Заглушка для модели

    @abstractmethod
    def predict(self, data: Dict[str, Any]) -> Any:
        if not data:
            raise ValueError("Данные для предсказания не могут быть пустыми")
        pass

    @staticmethod
    def validate_features(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return items


class MLRequestService:
    def __init__(self, predictor: MLEngine, billing: BillingService):
        self._predictor = predictor
        self._billing = billing

    def process_request(self, user: User, request: MLRequest):
        # 1. Проверка валидности входных данных
        if not request.input_data:
            request.fail("Input data is missing")
            user.add_history(request)
            raise ValueError("Невозможно обработать пустой запрос")

        # 2. Резервирование средств (Hold)
        self._billing.hold_funds(user, request.cost)

        try:
            # 3. Обработка запроса
            request.status = RequestStatus.PROCESSING
            result = self._predictor.predict(request.input_data)

            if result is None:
                raise RuntimeError("Модель не вернула результат")

            request.complete(result)

            # 4. Фиксация оплаты (списание из резерва)
            self._billing.create_payment(user, request.cost, request.id, from_hold=True)

            # 5. Сохранение результата в историю
            user.add_history(request)

        except Exception as e:
            # В случае ошибки отменяем резерв
            self._billing.void_hold(user, request.cost)
            request.fail(str(e))
            user.add_history(request)
            raise
