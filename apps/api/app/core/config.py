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
            if len(self.SECRET_KEY) < 32:
                print(  # noqa: T201
                    "FATAL: SECRET_KEY must be at least 32 characters in production.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if not self.CLERK_SECRET_KEY:
                print(  # noqa: T201
                    "FATAL: CLERK_SECRET_KEY is required in production.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if not self.SENTRY_DSN:
                import warnings
                warnings.warn(
                    "SENTRY_DSN not set in production — errors will be invisible",
                    stacklevel=2,
                )
        return self

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://scr_user:scr_password@localhost:5432/scr_platform"
    DATABASE_URL_SYNC: str = "postgresql://scr_user:scr_password@localhost:5432/scr_platform"
    # Optional read replica — if unset, all reads go to the primary
    DATABASE_URL_READ_REPLICA: str | None = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # ElasticSearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # Auth (Clerk)
    CLERK_SECRET_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""
    CLERK_ISSUER_URL: str = ""  # e.g. "https://your-app.clerk.accounts.dev"
    # 5 min TTL balances security (revoked JWTs invalid within 5 min) vs performance (fewer fetches)
    CLERK_JWKS_CACHE_TTL: int = 300  # seconds to cache JWKS public keys

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
    FRED_API_KEY: str = ""                  # St. Louis Fed FRED — https://fred.stlouisfed.org/docs/api/api_key.html
    ALPHA_VANTAGE_API_KEY: str = ""         # Alpha Vantage — https://www.alphavantage.co/support/#api-key
    # New external data connectors (free / public — add key to activate live data)
    COMPANIES_HOUSE_API_KEY: str = ""       # UK Companies House — https://developer.company-information.service.gov.uk/
    ENTSOE_API_KEY: str = ""                # ENTSOE Transparency — https://transparency.entsoe.eu/usrm/user/createPublicUser
    OPENWEATHER_API_KEY: str = ""           # OpenWeather — https://openweathermap.org/api
    EMBER_API_KEY: str = ""                 # Ember EU ETS carbon data — https://ember-climate.org/data/apis/
    EIA_API_KEY: str = ""                   # US Energy Information Administration — https://www.eia.gov/opendata/
    # New external data connectors (subscription required — leave empty until keys are configured)
    IEA_API_KEY: str = ""                   # International Energy Agency — subscription required
    SP_GLOBAL_API_KEY: str = ""             # S&P Global Market Intelligence — subscription required
    BNEF_API_KEY: str = ""                  # Bloomberg NEF — subscription required
    MSCI_ESG_API_KEY: str = ""              # MSCI ESG Research — subscription required
    PREQIN_API_KEY: str = ""                # Preqin Pro — subscription required

    # Custom Domain (E03)
    CUSTOM_DOMAIN_CNAME_TARGET: str = "custom.scr.io"

    # Sentry error monitoring — set SENTRY_DSN to enable; no-op when unset
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "development"
    APP_VERSION: str | None = None  # e.g. "1.2.3" or git SHA — used as Sentry release tag

    # AI token budget enforcement (per org, per calendar month)
    AI_TOKEN_BUDGET_ENABLED: bool = True
    AI_TOKEN_BUDGET_FOUNDATION: int = 2_000_000
    AI_TOKEN_BUDGET_PROFESSIONAL: int = 20_000_000
    AI_TOKEN_BUDGET_ENTERPRISE: int = 200_000_000


settings = Settings()
