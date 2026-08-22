import pytest
from pydantic import SecretStr, ValidationError

from pressradar.config import Settings


def test_settings_use_safe_local_defaults() -> None:
    settings = Settings()

    assert settings.app_mode == "local"
    assert settings.api_port == 8000
    assert settings.media_provider == "simulated"
    assert settings.ai_provider == "ollama"
    assert settings.pitch_sender == "simulated"
    assert settings.notification_provider == "fake"
    assert settings.crm_provider == "fake"
    assert settings.analytics_provider == "sqlite"


def test_settings_reject_unknown_runtime_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(app_mode="production")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "values",
    [
        {"notification_provider": "twilio"},
        {"crm_provider": "hubspot"},
    ],
)
def test_settings_require_credentials_for_real_providers(values: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        Settings(**values)  # type: ignore[arg-type]


def test_settings_accept_explicit_real_provider_credentials() -> None:
    settings = Settings(
        notification_provider="twilio",
        twilio_account_sid="AC123",
        twilio_auth_token=SecretStr("twilio-secret"),
        twilio_from_number="+15550000001",
        twilio_to_number="+15550000002",
        crm_provider="hubspot",
        hubspot_access_token=SecretStr("hubspot-secret"),
    )

    assert settings.notification_provider == "twilio"
    assert settings.crm_provider == "hubspot"


def test_settings_require_separate_operational_and_analytics_databases() -> None:
    with pytest.raises(ValidationError):
        Settings(database_path="data/shared.db", analytics_database_path="data/shared.db")
