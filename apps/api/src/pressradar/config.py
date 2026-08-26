from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, SecretStr, StringConstraints, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated settings loaded at the application boundary."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_mode: Literal["local", "integration", "gcp"] = "local"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_path: str = "data/pressradar.db"
    operational_provider: Literal["sqlite", "firestore"] = "sqlite"
    analytics_database_path: str = "data/analytics.db"
    session_ttl_hours: int = Field(default=168, ge=1, le=720)
    web_origin: str = "http://localhost:3000"
    media_provider: Literal["simulated"] = "simulated"
    ai_provider: Literal["fake", "ollama"] = "ollama"
    pitch_sender: Literal["simulated", "email"] = "simulated"
    email_provider: Literal["fake", "nodemailer"] = "fake"
    mailer_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:3001")
    mailer_internal_token: SecretStr | None = None
    notification_provider: Literal["fake", "twilio"] = "fake"
    crm_provider: Literal["fake", "hubspot"] = "fake"
    analytics_provider: Literal["none", "sqlite", "bigquery"] = "sqlite"
    gcp_project_id: str | None = None
    firestore_database: str = "(default)"
    bigquery_dataset: str = "pressradar_analytics"
    bigquery_events_table: str = "product_events"
    twilio_account_sid: str | None = None
    twilio_auth_token: SecretStr | None = None
    twilio_from_number: str | None = None
    hubspot_access_token: SecretStr | None = None
    newsapi_api_key: SecretStr | None = None
    external_provider_timeout_seconds: float = Field(default=10, gt=0, le=60)
    ollama_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434")
    ollama_model: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] = "qwen2.5:0.5b-instruct"
    ollama_translation_model: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ] = "translategemma:4b"
    ollama_timeout_seconds: float = Field(default=30, gt=0, le=300)

    @property
    def secure_cookies(self) -> bool:
        return self.app_mode == "gcp"

    @model_validator(mode="after")
    def validate_web_origin(self) -> "Settings":
        if self.app_mode == "gcp" and not self.web_origin.startswith("https://"):
            raise ValueError("WEB_ORIGIN must use HTTPS in gcp mode")
        return self

    @model_validator(mode="after")
    def validate_optional_providers(self) -> "Settings":
        if (
            self.analytics_provider == "sqlite"
            and self.analytics_database_path == self.database_path
        ):
            raise ValueError("Analytics and operational databases must be separate")
        twilio_values = (
            self.twilio_account_sid or "",
            "" if self.twilio_auth_token is None else self.twilio_auth_token.get_secret_value(),
            self.twilio_from_number or "",
        )
        if self.notification_provider == "twilio" and not all(
            value.strip() for value in twilio_values
        ):
            raise ValueError("Twilio credentials and sender phone number are required")
        hubspot_token = (
            ""
            if self.hubspot_access_token is None
            else self.hubspot_access_token.get_secret_value()
        )
        if self.crm_provider == "hubspot" and not hubspot_token.strip():
            raise ValueError("HUBSPOT_ACCESS_TOKEN is required")
        if self.email_provider == "nodemailer" and (
            self.mailer_internal_token is None
            or not self.mailer_internal_token.get_secret_value().strip()
        ):
            raise ValueError("MAILER_INTERNAL_TOKEN is required for Nodemailer")
        if self.pitch_sender == "email" and self.email_provider != "nodemailer":
            raise ValueError("PITCH_SENDER=email requires EMAIL_PROVIDER=nodemailer")
        if self.app_mode == "gcp":
            if not self.gcp_project_id or not self.gcp_project_id.strip():
                raise ValueError("GCP_PROJECT_ID is required in gcp mode")
            if self.operational_provider != "firestore":
                raise ValueError("OPERATIONAL_PROVIDER must be firestore in gcp mode")
            if self.analytics_provider != "bigquery":
                raise ValueError("ANALYTICS_PROVIDER must be bigquery in gcp mode")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
