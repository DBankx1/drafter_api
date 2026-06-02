"""
Conversation list cache backed by Redis.

Two-level caching strategy:

  Level 1 — Individual conversation: conv:{id}  (TTL: 10 min)
    Full ConversationItem dict. Populated on any DB fetch. Eviction via TTL only —
    conversations are immutable after creation, so explicit invalidation is unnecessary.

  Level 2 — Page result: conv_page:{business_id}:v{version}:{fingerprint}:{cursor}  (TTL: 2 min)
    Stores [conv_ids, next_cursor, has_more] for a specific query+cursor combination.
    The fingerprint encodes search, date range, sort, and limit — different filter sets
    get different cache keys, so they never collide.

  Level 2b — Total count: conv_count:{business_id}:v{version}:{fingerprint}  (TTL: 2 min)
    Count for a given filter combination. Shares the version mechanism.

Invalidation:
  Creating a new conversation calls bump_business_version(business_id), which increments
  conv_v:{business_id}. All page and count keys embed this version, so they become instant
  misses on the next read without a SCAN+DEL sweep. Old keys expire within their 2-min TTL.

  Individual conversation keys (Level 1) are never explicitly invalidated — TTL handles eviction.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Optional

from app.infrastructure.cache.redis_pool import get_redis_client

logger = logging.getLogger(__name__)

_CONV_TTL = 600     # 10 min — long because individual conversations never change
_PAGE_TTL = 120     # 2 min — short because list order changes when new convs arrive
_COUNT_TTL = 120    # 2 min — same reasoning as page


def _version_key(business_id: str) -> str:
    return f"conv_v:{business_id}"


def _conv_key(conv_id: str) -> str:
    return f"conv:{conv_id}"


def _page_key(business_id: str, version: str, fingerprint: str, cursor_key: str) -> str:
    return f"conv_page:{business_id}:v{version}:{fingerprint}:{cursor_key}"


def _count_key(business_id: str, version: str, fingerprint: str) -> str:
    return f"conv_count:{business_id}:v{version}:{fingerprint}"


def filter_fingerprint(
    search: Optional[str],
    started_at_from: Optional[datetime],
    started_at_to: Optional[datetime],
    sort: str,
    limit: int,
) -> str:
    """MD5 fingerprint of the filter combination — used as part of the cache key."""
    payload = {
        "s": search,
        "f": started_at_from.isoformat() if started_at_from else None,
        "t": started_at_to.isoformat() if started_at_to else None,
        "o": sort,
        "l": limit,
    }
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


async def get_business_version(business_id: str) -> str:
    """Returns the current version string for this business ('0' if not yet set). Never raises."""
    try:
        r = get_redis_client()
        v = await r.get(_version_key(business_id))
        return v if v is not None else "0"
    except Exception:
        logger.warning(f"[cache] Version read failed for business={business_id}", exc_info=True)
        return "0"


async def bump_business_version(business_id: str) -> None:
    """
    Increments the business version counter, logically invalidating all page and count
    caches for this business without issuing a SCAN+DEL sweep. Never raises.
    """
    try:
        r = get_redis_client()
        await r.incr(_version_key(business_id))
        logger.debug(f"[cache] Bumped conversation version for business={business_id}")
    except Exception:
        logger.warning(f"[cache] Version bump failed for business={business_id}", exc_info=True)


async def get_cached_conversation(conv_id: str) -> Optional[dict[str, Any]]:
    """Returns the cached conversation dict or None on miss/error. Never raises."""
    try:
        r = get_redis_client()
        raw = await r.get(_conv_key(conv_id))
        return json.loads(raw) if raw else None
    except Exception:
        logger.warning(f"[cache] Conv read failed conv={conv_id}", exc_info=True)
        return None


async def set_cached_conversation(conv_id: str, data: dict[str, Any]) -> None:
    """Stores an individual conversation. Never raises."""
    try:
        r = get_redis_client()
        await r.set(_conv_key(conv_id), json.dumps(data, default=str), ex=_CONV_TTL)
    except Exception:
        logger.warning(f"[cache] Conv write failed conv={conv_id}", exc_info=True)


async def get_cached_page(
    business_id: str,
    version: str,
    fingerprint: str,
    cursor_key: str,
) -> Optional[dict[str, Any]]:
    """Returns {conv_ids, next_cursor, has_more} or None on miss/error. Never raises."""
    try:
        r = get_redis_client()
        raw = await r.get(_page_key(business_id, version, fingerprint, cursor_key))
        return json.loads(raw) if raw else None
    except Exception:
        logger.warning(f"[cache] Page read failed business={business_id}", exc_info=True)
        return None


async def set_cached_page(
    business_id: str,
    version: str,
    fingerprint: str,
    cursor_key: str,
    conv_ids: list[str],
    next_cursor: Optional[str],
    has_more: bool,
) -> None:
    """Stores page metadata. Never raises."""
    try:
        r = get_redis_client()
        payload = json.dumps({"conv_ids": conv_ids, "next_cursor": next_cursor, "has_more": has_more})
        await r.set(
            _page_key(business_id, version, fingerprint, cursor_key),
            payload,
            ex=_PAGE_TTL,
        )
    except Exception:
        logger.warning(f"[cache] Page write failed business={business_id}", exc_info=True)


async def get_cached_count(
    business_id: str,
    version: str,
    fingerprint: str,
) -> Optional[int]:
    """Returns the cached total count or None on miss/error. Never raises."""
    try:
        r = get_redis_client()
        raw = await r.get(_count_key(business_id, version, fingerprint))
        return int(raw) if raw is not None else None
    except Exception:
        logger.warning(f"[cache] Count read failed business={business_id}", exc_info=True)
        return None


async def set_cached_count(
    business_id: str,
    version: str,
    fingerprint: str,
    count: int,
) -> None:
    """Stores the total count for a filter combination. Never raises."""
    try:
        r = get_redis_client()
        await r.set(_count_key(business_id, version, fingerprint), str(count), ex=_COUNT_TTL)
    except Exception:
        logger.warning(f"[cache] Count write failed business={business_id}", exc_info=True)
