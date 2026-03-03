import sys
from logging.config import fileConfig
from pathlib import Path

# Ensure apps/api is on sys.path so `app` package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool

from app.core.config import settings
from app.core.database import Base

import app.models  # noqa: F401 — register all models so Base.metadata is populated

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# configparser treats % as interpolation syntax — escape any % in the URL
# (URL-encoded passwords like %7C break set_main_option otherwise)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use create_engine directly to avoid configparser interpolation issues
    # with URL-encoded passwords containing % characters.
    connectable = create_engine(settings.DATABASE_URL_SYNC, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
