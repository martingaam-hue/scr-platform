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
    PORT: int = 8001

    # Sentry error monitoring
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "development"

    # Auth
    AI_GATEWAY_API_KEY: str = "internal-dev-key-change-in-production"

    # LLM Providers — 5-provider routing (Anthropic, Google, xAI, DeepSeek, OpenAI)
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""      # Gemini (google/gemini-*) — also accepts GEMINI_API_KEY
    XAI_API_KEY: str = ""         # xAI Grok (xai/grok-*) — from console.x.ai
    DEEPSEEK_API_KEY: str = ""    # DeepSeek (deepseek/deepseek-chat) — NON-SENSITIVE tasks only

    # Model defaults
    AI_DEFAULT_MODEL: str = "anthropic/claude-sonnet-4-5-20250929"
    AI_FALLBACK_MODEL: str = "openai/gpt-4o"
    AI_EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Rate limiting (requests/hour per org tier)
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_FOUNDATION_RPH: int = 100    # requests per hour
    RATE_LIMIT_PROFESSIONAL_RPH: int = 500
    RATE_LIMIT_ENTERPRISE_RPH: int = 2000
    RATE_LIMIT_FOUNDATION_TPD: int = 500_000    # tokens per day
    RATE_LIMIT_PROFESSIONAL_TPD: int = 2_000_000
    RATE_LIMIT_ENTERPRISE_TPD: int = 10_000_000

    # Vector store
    VECTOR_STORE_BACKEND: str = "memory"  # "pinecone" | "memory"
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "scr-platform"

    # External data feeds
    FRED_API_KEY: str = ""
    WORLD_BANK_BASE_URL: str = "https://api.worldbank.org/v2"
    NOAA_TOKEN: str = ""
    REGULATIONS_GOV_API_KEY: str = ""


settings = Settings()
