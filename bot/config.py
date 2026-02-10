import os
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class BotInternalSettings(BaseModel):
    TOKEN: str = "your_bot_token_here"
    API_URL: str = "http://app:8000"

class SeedSettings(BaseModel):
    DEMO_EMAIL: str = "demo@example.org"
    DEMO_PASSWORD: str = "password"

class BotConfig(BaseSettings):
    bot: BotInternalSettings = BotInternalSettings()
    seed: SeedSettings = SeedSettings()

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
        env_prefix=""
    )

settings = BotConfig()
