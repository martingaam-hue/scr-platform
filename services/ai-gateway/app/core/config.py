from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    API_URL: str = "http://localhost:8000"

    # Auth
    AI_GATEWAY_API_KEY: str = "internal-dev-key-change-in-production"

    # LLM Providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Model defaults
    AI_DEFAULT_MODEL: str = "claude-sonnet-4-20250514"
    AI_FALLBACK_MODEL: str = "gpt-4o"
    AI_EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Rate limiting
    REDIS_URL: str = "redis://localhost:6379/0"

    # Tier limits (requests per minute)
    RATE_LIMIT_FREE: int = 10
    RATE_LIMIT_PRO: int = 60
    RATE_LIMIT_ENTERPRISE: int = 300


settings = Settings()
