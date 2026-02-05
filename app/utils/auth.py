import hashlib

def get_password_hash(password: str) -> str:
    """Простое хеширование пароля с помощью SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка совпадения пароля с хешем."""
    return get_password_hash(plain_password) == hashed_password
