"""
Message list cache backed by Redis.

Caching strategy:
- Always store the ascending list (oldest-first — natural chat order).
- For descending requests: reverse the cached list in Python (O(n), n < 200 in practice).
  This halves storage and means invalidation only ever touches one key per conversation.

Invalidation:
- Write-through: memory_node invalidates the key after every turn (new messages written).
  This is the primary mechanism — the cache reflects DB within milliseconds.
- TTL: 5-minute safety net. Handles edge cases where invalidation is skipped due to
  an unhandled exception, and naturally evicts caches for idle conversations.

TTL reasoning:
- Active conversations: invalidated on every agent turn, so TTL is never the limiter.
- Idle conversations (no new messages): 5 min is a reasonable staleness window for a
  dashboard view. Could be extended to hours for read-heavy scenarios.
"""

import json
import logging
from typing import Any, Optional

from app.infrastructure.cache.redis_pool import get_redis_client

logger = logging.getLogger(__name__)

_KEY_PREFIX = "msgs"
_TTL_SECONDS = 300  # 5 minutes — primary invalidation is write-through via memory_node


def _cache_key(conversation_id: str) -> str:
    return f"{_KEY_PREFIX}:{conversation_id}"


async def get_cached_messages(conversation_id: str) -> Optional[list[dict[str, Any]]]:
    """
    Returns the cached message list (ascending order) or None on miss/error.
    Never raises.
    """
    try:
        r = get_redis_client()
        cached = await r.get(_cache_key(conversation_id))
        if cached:
            return json.loads(cached)
        return None
    except Exception:
        logger.warning(
            f"[cache] Message read failed for conversation={conversation_id}, continuing without cache",
            exc_info=True,
        )
        return None


async def set_cached_messages(
    conversation_id: str, messages_asc: list[dict[str, Any]]
) -> None:
    """
    Stores the ascending message list. Never raises — a write failure is non-critical;
    the next read will fall through to DB and attempt to cache again.
    """
    try:
        r = get_redis_client()
        await r.set(_cache_key(conversation_id), json.dumps(messages_asc, default=str), ex=_TTL_SECONDS)
    except Exception:
        logger.warning(
            f"[cache] Message write failed for conversation={conversation_id}",
            exc_info=True,
        )


async def invalidate_messages(conversation_id: str) -> None:
    """
    Deletes the cached message list for a conversation.
    Called by memory_node after each turn so the next API read gets fresh data.
    Never raises.
    """
    try:
        r = get_redis_client()
        deleted = await r.delete(_cache_key(conversation_id))
        if deleted:
            logger.debug(f"[cache] Message cache invalidated for conversation={conversation_id}")
    except Exception:
        logger.warning(
            f"[cache] Message invalidation failed for conversation={conversation_id}",
            exc_info=True,
        )
