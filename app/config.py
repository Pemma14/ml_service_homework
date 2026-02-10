import os
from decimal import Decimal
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
    MAX_REPLENISH_AMOUNT: Decimal = Decimal("50000.0")
    DEFAULT_REQUEST_COST: Decimal = Decimal("10.0")


class AuthSettings(BaseModel):
    SECRET_KEY: str = "your_secret_key_here_make_it_long_and_secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    COOKIE_NAME: str = "ml_service_session"
    SECURE_COOKIE: bool = True


class LoggingSettings(BaseModel):
    LEVEL: str = "INFO"
    FORMAT: str = "JSON"


class CORSSettings(BaseModel):
    ORIGINS: list[str] = ["http://localhost:3000"]


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


class MQSettings(BaseModel):
    HOST: str = "rabbitmq"
    PORT: int = 5672
    VIRTUAL_HOST: str = "/"
    USER: str = "guest"
    PASSWORD: str = "guest"
    # Очереди/обменники для задач
    QUEUE_NAME: str = "ml_task_queue"
    RPC_QUEUE_NAME: str = "rpc_queue"
    EXCHANGE_NAME: str = "ml_tasks_exchange"
    # Очередь/обменник для результатов
    RESULTS_EXCHANGE_NAME: str = "ml_results_exchange"
    RESULTS_QUEUE_NAME: str = "ml_results_queue"
    RESULTS_ROUTING_KEY: str = "ml_results_queue"
    # Ретрай и соединение
    RETRY_ATTEMPTS: int = 3
    RETRY_MULTIPLIER: float = 0.5
    RETRY_MIN: int = 1
    RETRY_MAX: int = 5
    HEARTBEAT: int = 30
    TIMEOUT: int = 2

    @property
    def amqp_url(self) -> str:
        """Формирует URL для подключения (удобно для aio-pika)."""
        return f"amqp://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}{self.VIRTUAL_HOST}?heartbeat={self.HEARTBEAT}"


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
    mq: MQSettings = MQSettings()
    logging: LoggingSettings = LoggingSettings()
    cors: CORSSettings = CORSSettings()

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
