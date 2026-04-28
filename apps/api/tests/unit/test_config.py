from faceless.config import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x:y@h/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("S3_ACCESS_KEY", "ak")
    monkeypatch.setenv("S3_SECRET_KEY", "sk")
    monkeypatch.setenv("CLERK_JWT_ISSUER", "https://example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "https://app.example.com")
    monkeypatch.setenv("ENCRYPTION_KEY", "0" * 44)

    settings = Settings()

    assert settings.database_url == "postgresql+asyncpg://x:y@h/db"
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.s3_bucket == "test-bucket"
    assert settings.clerk_jwt_issuer == "https://example.clerk.accounts.dev"
    assert settings.log_level == "info"
    assert settings.environment == "dev"


def test_settings_missing_required_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings()
