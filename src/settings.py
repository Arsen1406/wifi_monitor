from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    WIFI_NAME: str = Field(..., env="WIFI_NAME")
    TELEGRAM_TOKEN: str = Field(..., env="TELEGRAM_TOKEN")
    CHAT_IDS: List[str] = Field(default_factory=list, env="CHAT_IDS")

    CHECK_INTERVAL: int = Field(300, env="CHECK_INTERVAL")
    ACTIVE_CHECK_INTERVAL: int = Field(60, env="ACTIVE_CHECK_INTERVAL")
    MAX_FAILURES: int = Field(3, env="MAX_FAILURES")
    FAILURE_PAUSE: int = Field(3600, env="FAILURE_PAUSE")

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'


settings = Settings()
