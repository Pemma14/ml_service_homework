from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from app.config import settings
from app.utils import TokenExpiredException, IncorrectTokenFormatException

def create_access_token(user: str) -> str:
    payload = {
        "sub": user,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    token = jwt.encode(payload, settings.auth.SECRET_KEY, algorithm=settings.auth.ALGORITHM)
    return token

def verify_access_token(token: str) -> dict:
    try:
        data = jwt.decode(token, settings.auth.SECRET_KEY, algorithms=[settings.auth.ALGORITHM])
        return data
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException
    except JWTError:
        raise IncorrectTokenFormatException
