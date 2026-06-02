import logging
from datetime import datetime
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Query, Request, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middlewares.business_auth import get_user_business
from app.core.rate_limiting import rate_limit
from app.infrastructure.database.db import get_db
from app.models.dto.chat import (
    ConversationsResponse,
    MessagesResponse,
    StartConversationRequest,
    StartConversationResponse,
)
from app.models.entity.business import BusinessEntity
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"], prefix="/chat")
logger = logging.getLogger(__name__)

DbDep = Annotated[AsyncSession, Depends(get_db)]
BusinessDep = Annotated[BusinessEntity, Depends(get_user_business)]


@router.post(
    "/conversations/{business_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation",
    description="Called by the widget on load to create a conversation before opening the WebSocket.",
)
@rate_limit("10/hour")
async def start_conversation(
    request: Request,
    business_id: str,
    body: StartConversationRequest,
    db: DbDep,
) -> StartConversationResponse:
    return await ChatService(db).create_conversation(business_id, body)

@router.get(
    "/conversations",
    summary="List conversations for the authenticated business",
    description="""
Cursor-paginated list of conversations. Supports search, date-range filtering, and sort order.

**Pagination:** Pass `next_cursor` from the previous response as `cursor` to load the next page.
`has_more=true` means another page exists. Omit `cursor` for the first page.

**Search:** `search` matches against customer name or email (case-insensitive, partial match).

**Date range:** `started_at_from` / `started_at_to` accept ISO 8601 datetimes (e.g. `2024-01-01T00:00:00Z`).

**Caching:** Results are served from Redis. Creating a new conversation automatically
invalidates the list cache so the next read reflects the new data.
""",
)
async def get_conversations(
    business: BusinessDep,
    db: DbDep,
    cursor: Optional[str] = Query(
        default=None,
        description="Opaque pagination token from the previous response. Omit for the first page.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Number of conversations per page.",
    ),
    sort: Literal["asc", "desc"] = Query(
        default="desc",
        description="Sort order by started_at. 'desc' = newest first.",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Case-insensitive search against customer name or email.",
        max_length=200,
    ),
    started_at_from: Optional[datetime] = Query(
        default=None,
        description="Return conversations started at or after this datetime (ISO 8601).",
    ),
    started_at_to: Optional[datetime] = Query(
        default=None,
        description="Return conversations started at or before this datetime (ISO 8601).",
    ),
) -> ConversationsResponse:
    return await ChatService(db).get_conversations(
        business_id=business.id,
        limit=limit,
        sort=sort,
        search=search,
        started_at_from=started_at_from,
        started_at_to=started_at_to,
        cursor=cursor,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    summary="Get paginated messages for a conversation",
    description="""
Returns messages in one of two pagination modes, selected via `mode`:

**Cursor mode** (`mode=cursor`) — for the chat widget:
- First load (no `cursor`): returns the last `limit` messages (bottom of conversation).
- Subsequent loads: pass `cursor` from the previous response to load older messages.
- `next_cursor` in the response is the cursor for the next batch of older messages.
- `has_more` indicates whether older messages exist before the current batch.

**Offset mode** (`mode=offset`, default) — for the business dashboard:
- Standard `page` / `size` navigation. Supports jumping to arbitrary pages.
- `pages` in the response gives the total page count.

Both modes share one Redis cache entry per conversation. All pages are served
from the same cache — invalidated after every agent turn.
""",
)
async def get_conversation_messages(
    conversation_id: str,
    db: DbDep,
    business: BusinessDep,
    mode: Literal["cursor", "offset"] = Query(
        default="offset",
        description="Pagination mode. Use 'cursor' for the chat widget, 'offset' for the dashboard.",
    ),
    order: Literal["asc", "desc"] = Query(
        default="asc",
        description="Message order. 'asc' = oldest first (natural chat display).",
    ),
    # --- Cursor mode params ---
    cursor: Optional[str] = Query(
        default=None,
        description="[Cursor mode] Opaque token from the previous response. Omit for the first load.",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="[Cursor mode] Number of messages to return per batch.",
    ),
    # --- Offset mode params ---
    page: int = Query(
        default=1,
        ge=1,
        description="[Offset mode] Page number (1-based).",
    ),
    size: int = Query(
        default=50,
        ge=1,
        le=200,
        description="[Offset mode] Messages per page.",
    ),
) -> MessagesResponse:
    return await ChatService(db).get_messages(
        conversation_id=conversation_id,
        business_id=business.id,
        order=order,
        mode=mode,
        cursor=cursor,
        limit=limit,
        page=page,
        size=size,
    )


@router.websocket("/ws/{business_id}/{conversation_id}")
async def chat(
    websocket: WebSocket,
    business_id: str,
    conversation_id: str,
    db: DbDep,
) -> None:
    await ChatService(db).handle_chat_message(websocket, business_id, conversation_id)
