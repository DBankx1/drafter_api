"""
Centralised rate-limiting primitives for the whole application.

HTTP rate limiting — slowapi with Redis backend:
    from app.core.rate_limiting import rate_limit

    @router.post("/some-endpoint")
    @rate_limit("10/hour")
    async def my_route(request: Request, ...):
        ...

    The `request: Request` parameter is required by slowapi to extract the
    caller's IP address. It does not need to be used in the route body.

WebSocket turn semaphore:
    from app.core.rate_limiting import ws_semaphore

    acquired = await ws_semaphore.acquire(conversation_id)
    try:
        ...
    finally:
        await ws_semaphore.release(conversation_id)
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.infrastructure.cache.redis_pool import get_redis_client


# ---------------------------------------------------------------------------
# HTTP limiter
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.REDIS_URL)


def rate_limit(limit_string: str):
    """
    Decorator factory for per-IP HTTP rate limiting.

    Usage:
        @rate_limit("10/hour")
        async def my_route(request: Request, ...): ...

    Any slowapi limit string is valid: "5/minute", "100/day", etc.
    The route must declare `request: Request` as a parameter.
    """
    return limiter.limit(limit_string)


# ---------------------------------------------------------------------------
# WebSocket turn semaphore
# ---------------------------------------------------------------------------

class ConversationSemaphore:
    """
    Redis-backed mutex that enforces one-turn-at-a-time per conversation.

    Uses SET NX EX — atomic, no race conditions. The TTL auto-releases the
    lock if the server crashes mid-turn so the conversation is never stuck.
    """

    _PREFIX = "ws_turn:"
    _TTL = 120  # seconds — 2× the max expected agent turn duration

    async def acquire(self, conversation_id: str) -> bool:
        """Returns True if the lock was acquired, False if already held."""
        r = get_redis_client()
        return bool(
            await r.set(f"{self._PREFIX}{conversation_id}", "1", nx=True, ex=self._TTL)
        )

    async def release(self, conversation_id: str) -> None:
        """Releases the lock. Safe to call even if the lock was never acquired."""
        await get_redis_client().delete(f"{self._PREFIX}{conversation_id}")


ws_semaphore = ConversationSemaphore()
