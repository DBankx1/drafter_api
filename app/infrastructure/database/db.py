import os

from fastapi.concurrency import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.entity.base import Base
from sqlalchemy import text
from sqlalchemy.pool import NullPool


async def _on_connect(conn, _):
    """Register pgvector type with asyncpg on every new connection."""
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

def _get_engine():
    """
    Workers get NullPool — no connection reuse between tasks.
    API gets the default pool — efficient for concurrent requests.
    """
    is_worker = os.getenv("IS_CELERY_WORKER", "false").lower() == "true"

    if is_worker:
        return create_async_engine(
            settings.DB_URL,
            poolclass=NullPool,
            future=True,
            echo=False,
        )

    return create_async_engine(
        settings.DB_URL,
        future=True,
        echo=False,
        pool_size=10,
        max_overflow=20,
    )

engine = _get_engine()

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def init_db():
    async with engine.begin() as conn:
        await _on_connect(conn, None)  # Ensure pgvector is registered before creating tables
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@asynccontextmanager
async def get_db_context():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()