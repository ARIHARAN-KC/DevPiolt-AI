
from app.core.config import Settings


def test_settings_use_safe_development_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "DevPilot AI"
    assert settings.app_env == "development"
    assert settings.database_url is None
    assert settings.llm_provider == "mock"
    assert settings.sandbox_provider == "mock"


def test_settings_accept_explicit_values() -> None:
    settings = Settings(
        _env_file=None,
        app_name="Test Agent",
        database_url="postgresql+psycopg://example",
        llm_provider="mock",
    )

    assert settings.app_name == "Test Agent"
    assert settings.database_url == "postgresql+psycopg://example"
