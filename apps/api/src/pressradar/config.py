from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated settings loaded at the application boundary."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_mode: Literal["local", "integration", "gcp"] = "local"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_path: str = "data/pressradar.db"
    session_ttl_hours: int = Field(default=168, ge=1, le=720)
    web_origin: str = "http://localhost:3000"
    media_provider: Literal["simulated"] = "simulated"

    @property
    def secure_cookies(self) -> bool:
        return self.app_mode == "gcp"

    @model_validator(mode="after")
    def validate_web_origin(self) -> "Settings":
        if self.app_mode == "gcp" and not self.web_origin.startswith("https://"):
            raise ValueError("WEB_ORIGIN must use HTTPS in gcp mode")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
