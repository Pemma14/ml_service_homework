import os
from functools import lru_cache
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseModel):
    NAME: str = "ML Service API"
    DESCRIPTION: str = "Сервис для выполнения предсказаний на основе моделей машинного обучения"
    VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    MODE: str = "DEV"


class AuthSettings(BaseModel):
    SECRET_KEY: str = "your_secret_key_here_make_it_long_and_secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    COOKIE_NAME: str = "access_token"


class DbSettings(BaseModel):
    HOST: str = "database"
    PORT: int = 5432
    USER: str = "pema"
    PASSWORD: str = "password"
    NAME: str = "ml_service"
    ECHO: bool = True
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_RECYCLE: int = 3600
    POOL_PRE_PING: bool = True

    @property
    def url_psycopg(self) -> str:
        return f"postgresql+psycopg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"

    @property
    def url_asyncpg(self) -> str:
        return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"

    def get_engine_kwargs(self) -> dict:
        """Формирует параметры для создания движка SQLAlchemy."""
        return {
            "url": self.url_psycopg,
            "echo": self.ECHO,
            "pool_size": self.POOL_SIZE,
            "max_overflow": self.MAX_OVERFLOW,
            "pool_recycle": self.POOL_RECYCLE,
            "pool_pre_ping": self.POOL_PRE_PING
        }


class SeedSettings(BaseModel):
    ADMIN_EMAIL: str = "admin@example.org"
    ADMIN_PASSWORD: str = "password"
    DEMO_EMAIL: str = "demo@example.org"
    DEMO_PASSWORD: str = "password"


class Settings(BaseSettings):
    app: AppSettings = AppSettings()
    db: DbSettings = DbSettings()
    seed: SeedSettings = SeedSettings()
    auth: AuthSettings = AuthSettings()
    bot_token: str = "your_bot_token_here"
    api_url: str = "http://app:8000"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
        env_prefix=""
    )


# Создадим кеш для функции создания объекта класса Settings
@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Создадим объект настроек
settings = get_settings()
