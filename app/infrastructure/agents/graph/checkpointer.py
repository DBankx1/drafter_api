from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.redis import AsyncRedisSaver

from app.core.config import settings

CONVERSATION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


@asynccontextmanager
async def get_checkpointer() -> AsyncIterator[AsyncRedisSaver]:
    """
    Async context manager that yields a configured Redis checkpointer.
    Use inside FastAPI lifespan so the connection stays open for app lifetime.

    Each conversation_id maps to a LangGraph thread_id — the checkpointer
    loads/saves state automatically on every graph invocation. No manual
    Redis reads or writes are needed.
    """
    async with AsyncRedisSaver.from_conn_string(
        settings.REDIS_URL,
        ttl={"default_ttl": CONVERSATION_TTL_SECONDS},
    ) as checkpointer:
        await checkpointer.asetup()
        yield checkpointer
