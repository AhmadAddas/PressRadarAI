import pytest
from pydantic import ValidationError

from pressradar.config import Settings


def test_settings_use_safe_local_defaults() -> None:
    settings = Settings()

    assert settings.app_mode == "local"
    assert settings.api_port == 8000
    assert settings.media_provider == "simulated"
    assert settings.ai_provider == "ollama"


def test_settings_reject_unknown_runtime_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(app_mode="production")  # type: ignore[arg-type]
