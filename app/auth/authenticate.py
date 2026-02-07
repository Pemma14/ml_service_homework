from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from app.auth.jwt_handler import verify_access_token
from app.utils import TokenAbsentException
from app.config import settings

class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request):
        token = await super().__call__(request)
        if not token:
            token = request.cookies.get(settings.auth.COOKIE_NAME)
        return token

#Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login", auto_error=False)

async def authenticate(token: str = Depends(oauth2_scheme)):
    if not token:
        raise TokenAbsentException
    return verify_access_token(token)["sub"]

# Схема OAuth2 для получения токена из cookie
oauth2_scheme_cookie = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/users/login", auto_error=False)
async def authenticate_cookie(token: str = Depends(oauth2_scheme_cookie)):
    if not token:
        raise TokenAbsentException
    return verify_access_token(token.removeprefix("Bearer "))["sub"]
