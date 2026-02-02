from app.utils.exceptions import (
    AppException,
    InsufficientFundsException,
    InternalServerErrorException,
    MLInferenceException,
    MLInvalidDataException,
    MLModelLoadException,
    MLModelNotFoundException,
    MLRequestNotFoundException,
    ServiceUnavailableException,
    UserAlreadyExistsException,
    UserIsNotPresentException,
)
from app.utils.handlers import setup_exception_handlers
