from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models import User, UserRole
from app.utils import UserIsNotPresentException, ForbiddenException
from app.auth.authenticate import authenticate
from app.services import MLRequestService, BillingService, UserService, AdminService


def get_ml_request_service(session: Session = Depends(get_session)) -> MLRequestService:
    return MLRequestService(session)


def get_billing_service(session: Session = Depends(get_session)) -> BillingService:
    return BillingService(session)


def get_user_service(session: Session = Depends(get_session)) -> UserService:
    return UserService(session)


def get_admin_service(session: Session = Depends(get_session)) -> AdminService:
    return AdminService(session)


async def get_current_user(
    user_id: str = Depends(authenticate),
    user_service: UserService = Depends(get_user_service)
) -> User:
    user = user_service.get_user_by_id(int(user_id))

    if not user:
        raise UserIsNotPresentException

    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != UserRole.admin:
        raise ForbiddenException
    return current_user
