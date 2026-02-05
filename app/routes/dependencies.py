from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models import User
from app.services.user_service import get_user_by_id
from app.utils import (
    UserIsNotPresentException,
)

async def get_current_user(
    user_id: int = Query(..., description="ID пользователя"),
    session: Session = Depends(get_session)
) -> User:
    user = get_user_by_id(session, user_id)

    if not user:
        raise UserIsNotPresentException

    return user
