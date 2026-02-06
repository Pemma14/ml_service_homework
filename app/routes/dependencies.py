from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.database import get_session
from app.models import User
from app.services.user_service import get_user_by_id
from app.utils import UserIsNotPresentException
from app.auth.authenticate import authenticate

async def get_current_user(
    user_id: str = Depends(authenticate),
    session: Session = Depends(get_session)
) -> User:
    user = get_user_by_id(session, int(user_id))

    if not user:
        raise UserIsNotPresentException

    return user
