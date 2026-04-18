import asyncio
import sys
from pathlib import Path
from logging.config import fileConfig

# Ensure root package path is available when Alembic runs from repo root.
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context

from app.core.config import settings
from app.models.entity.base import Base

config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_database_url() -> str:
    # Uses the same settings object as the app
    # In env var-driven deployment, DB_URL is from .env or orchestration environment
    return settings.DB_URL


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(
        get_database_url(),
        future=True,
        echo=False,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda conn: context.configure(
                connection=conn,
                target_metadata=target_metadata,
                compare_type=True,
            )
        )

        async with connection.begin():
            await connection.run_sync(lambda conn: context.run_migrations())

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
