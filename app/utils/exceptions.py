from typing import Optional, Any
from fastapi import HTTPException, status

# Класс для исключений, которые связаны с нашим приложением
class AppException(HTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = ""

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)

# Исключения для работы с пользователями
class UserAlreadyExistsException(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь уже существует"

class UserIsNotPresentException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Пользователь не найден"

# Ошибки бизнес-логики
class InsufficientFundsException(AppException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    detail = "Недостаточно кредитов на балансе"

class MLRequestNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Запрос с таким ID не существует"

class MLModelNotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "ML-модель не найдена"

# Ошибки ML Engine
class MLModelLoadException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Ошибка при загрузке ML-модели"

class MLInferenceException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Ошибка во время выполнения предсказания"

class MLInvalidDataException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = "Некорректные данные для ML-модели"

    def __init__(self, errors: Optional[list[Any]] = None) -> None:
        super().__init__()
        if errors:
            self.detail = {"message": self.detail, "errors": errors}

# Исключения для аутентификации
class TokenAbsentException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Токен аутентификации отсутствует. Пожалуйста, войдите в систему."

class IncorrectTokenFormatException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный формат токена. Пожалуйста, войдите в систему снова."

class TokenExpiredException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Токен истек. Пожалуйста, войдите в систему снова."

class IncorrectEmailOrPasswordException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный email или пароль. Проверьте введенные данные и попробуйте снова."

class MQServiceException(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Сервис временно недоступен. Не удалось поставить задачу в очередь."

    def __init__(self, detail: Optional[str] = None) -> None:
        if detail:
            self.detail = detail
        super().__init__()

# Инфраструктурные ошибки
class InternalServerErrorException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Internal server error"

class ServiceUnavailableException(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    detail = "Service unavailable"

# Ошибки Телеграм-бота
class BotException(Exception):
    """Базовое исключение для бота."""
    pass



