from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.entity.base import Base
from sqlalchemy import text


async def _on_connect(conn, _):
    """Register pgvector type with asyncpg on every new connection."""
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    
engine = create_async_engine(settings.DB_URL, future=True, echo=False)

SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    future=True,
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
