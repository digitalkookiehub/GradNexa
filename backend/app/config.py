"""Application settings loaded from environment variables."""
import json
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings. No secrets are hardcoded; all come from env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "GradNexa"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@gradnexa.local"
    FRONTEND_URL: str = "http://localhost:5173"
    # Comma-separated list (or a JSON array). Parsed by cors_origins_list.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    RATE_LIMIT_ENABLED: bool = True
    LOGIN_RATE_LIMIT: str = "10/minute"
    REGISTER_RATE_LIMIT: str = "10/minute"
    FORGOT_PASSWORD_RATE_LIMIT: str = "5/minute"
    LOG_LEVEL: str = "INFO"
    # bcrypt work factor; production keeps >= 12. Tests lower it (minimum 4) to keep the suite fast.
    BCRYPT_ROUNDS: int = 12
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 10
    # RAG tuning defaults are UNCONFIRMED assumptions (no corpus yet) and are configurable.
    RAG_CHUNK_CHARS: int = 900
    RAG_CHUNK_OVERLAP_CHARS: int = 120
    RAG_MIN_QUERY_COVERAGE: float = 0.5

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS as a list; accepts a comma separated string or a JSON array."""
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("["):
            return [str(v).strip() for v in json.loads(raw) if str(v).strip()]
        return [v.strip() for v in raw.split(",") if v.strip()]

    @model_validator(mode="after")
    def enforce_production_safety(self) -> "Settings":
        """Refuse to start in production with weak or placeholder security settings."""
        if self.ENVIRONMENT.lower() != "production":
            return self
        problems: list[str] = []
        if len(self.SECRET_KEY) < 32 or "change" in self.SECRET_KEY.lower():
            problems.append("SECRET_KEY must be a random value of at least 32 characters")
        if not self.RATE_LIMIT_ENABLED:
            problems.append("RATE_LIMIT_ENABLED must be true")
        if self.BCRYPT_ROUNDS < 10:
            problems.append("BCRYPT_ROUNDS must be at least 10")
        if "*" in self.cors_origins_list:
            problems.append("CORS_ORIGINS must not contain '*'")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
