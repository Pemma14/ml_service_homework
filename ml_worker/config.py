import os
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class MQSettings(BaseModel):
    HOST: str = "rabbitmq"
    PORT: int = 5672
    VIRTUAL_HOST: str = "/"
    USER: str = "guest"
    PASSWORD: str = "guest"
    QUEUE_NAME: str = "ml_task_queue"
    RPC_QUEUE_NAME: str = "rpc_queue"
    RESULTS_EXCHANGE_NAME: str = "ml_results_exchange"
    RESULTS_QUEUE_NAME: str = "ml_results_queue"
    RESULTS_ROUTING_KEY: str = "ml_results_queue"
    HEARTBEAT: int = 30

    @property
    def amqp_url(self) -> str:
        """Формирует URL для подключения."""
        return f"amqp://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}{self.VIRTUAL_HOST}?heartbeat={self.HEARTBEAT}"

class DBSettings(BaseModel):
    HOST: str = "database"
    PORT: int = 5432
    USER: str = "pema"
    PASSWORD: str = "password"
    NAME: str = "ml_service"

    @property
    def url(self) -> str:
        return f"postgresql+psycopg2://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"

class BotSettings(BaseModel):
    API_URL: str = "http://app:8000"

class WorkerInternalSettings(BaseModel):
    PREFETCH_COUNT: int = 1
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    SAVE_METHOD: str = "mq"
    FEATURES_ORDER: list[str] = [
        "Возраст", "ВНН/ПП", "Клозапин",
        "CYP2C19 1/2", "CYP2C19 1/17", "CYP2C19 *17/*17", "CYP2D6 1/3"
    ]

class WorkerConfig(BaseSettings):
    mq: MQSettings = MQSettings()
    bot: BotSettings = BotSettings()
    db: DBSettings = DBSettings()
    worker: WorkerInternalSettings = WorkerInternalSettings()

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
        env_prefix=""
    )

settings = WorkerConfig()
