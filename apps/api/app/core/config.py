import sys

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "change-this-to-a-random-string-in-production"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    SECRET_KEY: str = _DEFAULT_SECRET
    API_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    AI_GATEWAY_URL: str = "http://localhost:8001"
    AI_GATEWAY_API_KEY: str = ""

    # Security
    RATE_LIMIT_ENABLED: bool = True
    MAX_REQUEST_BODY_BYTES: int = 52_428_800  # 50 MB

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.APP_ENV == "production":
            if self.SECRET_KEY == _DEFAULT_SECRET:
                print(  # noqa: T201
                    "FATAL: SECRET_KEY must be changed before running in production.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if not self.CLERK_SECRET_KEY:
                print(  # noqa: T201
                    "FATAL: CLERK_SECRET_KEY is required in production.",
                    file=sys.stderr,
                )
                sys.exit(1)
        return self

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

    # Salesforce OAuth
    SALESFORCE_CLIENT_ID: str = ""
    SALESFORCE_CLIENT_SECRET: str = ""
    SALESFORCE_REDIRECT_URI: str = ""

    # External Market Data
    FRED_API_KEY: str = ""            # St. Louis Fed FRED — https://fred.stlouisfed.org/docs/api/api_key.html
    ALPHA_VANTAGE_API_KEY: str = ""   # Alpha Vantage (optional)

    # Custom Domain (E03)
    CUSTOM_DOMAIN_CNAME_TARGET: str = "custom.scr.io"


settings = Settings()
