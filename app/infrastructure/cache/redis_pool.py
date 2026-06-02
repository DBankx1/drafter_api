"""
Shared Redis connection pool for the whole application.

A single pool is created lazily on first use and reused across all cache modules.
This avoids duplicate pools and keeps total Redis connections bounded and predictable.

Usage in cache modules:
    from app.infrastructure.cache.redis_pool import get_redis_client
    r = get_redis_client()
"""

from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_pool: Optional[aioredis.ConnectionPool] = None


def _get_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,   # headroom for checkpointer + both caches + Celery
            decode_responses=True,
        )
    return _pool


def get_redis_client() -> aioredis.Redis:
    """Returns a client drawing from the shared pool. No new connection is created per call."""
    return aioredis.Redis(connection_pool=_get_pool())
