import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models import User
from app.routes.dependencies import get_current_user
from app.schemas.user_schemas import SUserRegister, SUserAuth, SUser
from app.services import user_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description="Регистрирует нового пользователя в системе, хеширует пароль и сохраняет данные в базу.",
    response_description="Сообщение об успешной регистрации"
)
async def register_user(
    user_data: SUserRegister,
    session: Session = Depends(get_session)
):
    user_service.create_user(session, user_data)
    logger.info(f"User registered successfully: {user_data.email}")
    return {"message": "Вы успешно зарегистрированы!"}

@router.post(
    "/login",
    summary="Вход в систему",
    description="Аутентификация пользователя по email и паролю. Возвращает ID пользователя для последующих запросов.",
    response_description="Результат аутентификации и ID пользователя"
)
async def auth_user(
    user_data: SUserAuth,
    session: Session = Depends(get_session)
):
    user = user_service.authenticate_user(session, user_data.email, user_data.password)
    logger.info(f"User logged in: {user_data.email}")
    return {"message": "Вы успешно вошли в систему", "user_id": user.id}

@router.post(
    "/logout",
    summary="Выход из системы",
    description="Завершает текущую сессию пользователя (временно реализовано как заглушка).",
    response_description="Сообщение об успешном выходе"
)
async def logout_user():
    logger.info("User logged out")
    return {"message": "Вы успешно вышли из системы"}

@router.get(
    "/me",
    response_model=SUser,
    summary="Профиль пользователя",
    description="Возвращает детальную информацию о текущем авторизованном пользователе на основе переданного ID.",
    response_description="Данные текущего пользователя"
)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
