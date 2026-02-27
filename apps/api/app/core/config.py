from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    SECRET_KEY: str = "change-this-to-a-random-string-in-production"
    API_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    AI_GATEWAY_URL: str = "http://localhost:8001"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://scr_user:scr_password@localhost:5432/scr_platform"
    DATABASE_URL_SYNC: str = "postgresql://scr_user:scr_password@localhost:5432/scr_platform"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # ElasticSearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # Auth (Clerk)
    CLERK_SECRET_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""
    CLERK_ISSUER_URL: str = ""  # e.g. "https://your-app.clerk.accounts.dev"
    CLERK_JWKS_CACHE_TTL: int = 3600  # seconds to cache JWKS public keys

    # S3 / MinIO
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    AWS_S3_BUCKET: str = "scr-documents"
    AWS_S3_ENDPOINT_URL: str = "http://localhost:9000"
    AWS_S3_REGION: str = "us-east-1"


settings = Settings()
