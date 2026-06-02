"""
Service embedding cache backed by Redis.

Service texts (pricing catalogue) are deterministic per business — the same set of
services always produces the same embedding vectors. Caching them avoids a redundant
OpenAI API call on every user message.

Design decisions:
- Shared Redis connection pool from redis_pool module — one pool for the whole app.
- All operations are fire-and-forget on failure — a Redis outage degrades to
  re-computing embeddings; it never breaks the chat flow.
- SCAN instead of KEYS for pattern deletion — KEYS blocks the Redis event loop on
  large keyspaces; SCAN is cursor-based and production-safe.
- JSON serialisation — debuggable in redis-cli; compression not needed at this scale
  (~100KB per business per cache entry).
"""

import hashlib
import json
import logging
from typing import Optional

from app.core.config import settings
from app.infrastructure.cache.redis_pool import get_redis_client

logger = logging.getLogger(__name__)


def _client():
    return get_redis_client()


def _cache_key(business_id: str, service_texts: list[str]) -> str:
    """
    Stable, short cache key. SHA-256 of joined service texts so any change
    in the catalogue content produces a different key (natural invalidation).
    The explicit invalidate call handles the case where the same key is reused
    after re-adding the same services.
    """
    content_hash = hashlib.sha256("|".join(service_texts).encode()).hexdigest()[:16]
    return f"svc_emb:{business_id}:{content_hash}"


async def get_service_embeddings(
    business_id: str, service_texts: list[str]
) -> Optional[list[list[float]]]:
    """
    Returns cached embedding vectors or None on cache miss / error.
    Never raises — callers treat None as "compute it fresh".
    """
    try:
        r = _client()
        cached = await r.get(_cache_key(business_id, service_texts))
        if cached:
            return json.loads(cached)
        return None
    except Exception:
        logger.warning(
            f"[cache] Service embedding read failed for business={business_id}, continuing without cache",
            exc_info=True,
        )
        return None


async def set_service_embeddings(
    business_id: str,
    service_texts: list[str],
    embeddings: list[list[float]],
    ttl: int,
) -> None:
    """
    Stores embedding vectors with a TTL. Never raises — a write failure is non-critical;
    the next call will just re-compute and attempt to store again.
    """
    try:
        r = _client()
        await r.set(
            _cache_key(business_id, service_texts),
            json.dumps(embeddings),
            ex=ttl,
        )
    except Exception:
        logger.warning(
            f"[cache] Service embedding write failed for business={business_id}",
            exc_info=True,
        )


async def invalidate_service_embeddings(business_id: str) -> None:
    """
    Deletes all service embedding cache entries for a business.
    Called after any pricing config mutation so the next RAG call re-embeds fresh data.

    Uses SCAN (cursor-based) instead of KEYS (blocking) — safe on large Redis keyspaces.
    """
    try:
        r = _client()
        pattern = f"svc_emb:{business_id}:*"
        keys_to_delete = [key async for key in r.scan_iter(match=pattern, count=100)]
        if keys_to_delete:
            await r.delete(*keys_to_delete)
            logger.info(f"[cache] Invalidated {len(keys_to_delete)} service embedding key(s) for business={business_id}")
    except Exception:
        logger.warning(
            f"[cache] Service embedding invalidation failed for business={business_id}",
            exc_info=True,
        )
