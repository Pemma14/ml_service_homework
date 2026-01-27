from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass(frozen=True)
class PasswordHash:
    """Обёртка для хранения хеша пароля (Value Object)"""
    value: str

class PasswordHasher(ABC):
    """Абстрактный класс для хеширования паролей (Контракт)"""
    @abstractmethod
    def hash_password(self, password: str) -> PasswordHash:
        pass

    @abstractmethod
    def verify_password(self, password: str, hashed: PasswordHash) -> bool:
        pass
