import logging
from bisect import bisect_left
from datetime import datetime
from typing import Literal, Optional

from fastapi import HTTPException, WebSocket, status
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cache.conversation_cache import (
    bump_business_version,
    filter_fingerprint,
    get_business_version,
    get_cached_conversation,
    get_cached_count,
    get_cached_page,
    set_cached_conversation,
    set_cached_count,
    set_cached_page,
)
from app.infrastructure.cache.message_cache import get_cached_messages, set_cached_messages
from app.infrastructure.repository.business_repository import BusinessRepository
from app.infrastructure.repository.conversation_repository import ConversationRepository
from app.infrastructure.repository.message_repository import MessageRepository
from app.infrastructure.websockets.chat_socket_manager import ChatWebSocketManager
from app.models.dto.chat import (
    ConversationItem,
    ConversationsResponse,
    MessageResponse,
    MessagesResponse,
    StartConversationRequest,
    StartConversationResponse,
    decode_cursor,
    encode_cursor,
)
from app.models.entity.conversation import ConversationEntity

logger = logging.getLogger(__name__)

_WS_CLOSE_NOT_FOUND = 4004
_WS_CLOSE_FORBIDDEN = 4003


class ChatService:
    """
    Single service layer for all chat operations.

    Instantiated with only a DB session so it can serve both HTTP endpoints
    and WebSocket connections from the same class. Routes are thin adapters
    that delegate entirely to this service.
    """
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_conversation(
        self,
        business_id: str,
        body: StartConversationRequest,
    ) -> StartConversationResponse:
        """
        Creates a new conversation for a widget session.
        The returned conversation_id is used as the WebSocket path parameter.
        """
        business = await BusinessRepository(self.db).get_by_id(business_id)
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

        conversation = await ConversationRepository(self.db).create(
            business_id=business_id,
            customer_name=body.customer_name,
            customer_email=body.customer_email,
        )
        await bump_business_version(business_id)
        return StartConversationResponse(conversation_id=conversation.id)

    async def get_conversations(
        self,
        business_id: str,
        limit: int,
        sort: Literal["asc", "desc"],
        search: Optional[str],
        started_at_from: Optional[datetime],
        started_at_to: Optional[datetime],
        cursor: Optional[str],
    ) -> ConversationsResponse:
        """
        Returns a cursor-paginated list of conversations for a business.

        Cache path (happy path — two Redis reads):
          1. Read the business version counter.
          2. Read the page key (business + version + filter fingerprint + cursor).
          3. On page hit: read individual conv keys; batch-fetch any misses from DB.
          4. Count cached separately under the same version.

        Invalidation: creating a conversation bumps the version → all page/count
        keys for that business become instant misses without a SCAN+DEL sweep.
        """
        cursor_ts, cursor_id = self._decode_conv_cursor(cursor)
        version = await get_business_version(business_id)
        fingerprint = filter_fingerprint(search, started_at_from, started_at_to, sort, limit)
        cursor_key = cursor or "start"
        repo = ConversationRepository(self.db)

        page_cache = await get_cached_page(business_id, version, fingerprint, cursor_key)
        if page_cache is not None:
            return await self._conversations_from_page_cache(
                page_cache, repo, business_id, version, fingerprint,
                search, started_at_from, started_at_to, limit,
            )

        return await self._conversations_from_db(
            repo, business_id, limit, sort, search, started_at_from, started_at_to,
            cursor_ts, cursor_id, version, fingerprint, cursor_key,
        )

    async def get_messages(
        self,
        conversation_id: str,
        business_id: str,
        order: Literal["asc", "desc"],
        mode: Literal["cursor", "offset"],
        cursor: Optional[str],
        limit: int,
        page: int,
        size: int,
    ) -> MessagesResponse:
        """
        Returns a paginated message list in one of two modes selected by the caller:

        Cursor mode (cursor param provided or first widget load):
          - Initial load (no cursor): returns the last `limit` messages.
          - Subsequent loads (cursor given): returns `limit` messages older than the cursor.
          - Cursor is encoded as base64(timestamp:id) — opaque and URL-safe.
          - Binary search (O log n) locates the cursor in the cached list instantly.
          - next_cursor in the response points to the oldest message in the batch;
            pass it as ?cursor= to load the next page of older messages.

        Offset mode (cursor param absent):
          - Standard ?page=N&size=N pagination for the business dashboard.
          - Arithmetic slice from the cached list — O(1) after index calculation.

        Cache: always holds the full ascending list. Both pagination modes slice
        from it in memory — one cache entry serves every page of every mode.
        Write-through invalidation fires in memory_node after every agent turn.
        """
        conversation = await ConversationRepository(self.db).get_by_id(conversation_id)
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        if conversation.business_id != business_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        # --- Cache-first full list load (shared by both pagination modes) ---
        cached = await get_cached_messages(conversation_id)
        if cached is not None:
            messages_asc = [MessageResponse.model_validate(m) for m in cached]
        else:
            entities = await MessageRepository(self.db).get_by_conversation_id(
                conversation_id, ascending=True
            )
            messages_asc = [MessageResponse.model_validate(m, from_attributes=True) for m in entities]
            await set_cached_messages(
                conversation_id, [m.model_dump(mode="json") for m in messages_asc]
            )

        total = len(messages_asc)

        if cursor is not None or mode == "cursor":
            return self._paginate_cursor(messages_asc, cursor, limit, order, total)
        return self._paginate_offset(messages_asc, page, size, order, total)

    # ------------------------------------------------------------------ #
    #  WebSocket operation                                                 #
    # ------------------------------------------------------------------ #

    async def handle_chat_message(
        self,
        websocket: WebSocket,
        business_id: str,
        conversation_id: str,
    ) -> None:
        """
        Accepts and drives a WebSocket chat session.
        Validates the connection before accepting, then streams agent responses
        token-by-token until the client disconnects.
        """
        conversation, existing_proposal_id = await self._validate_connection(
            websocket, business_id, conversation_id
        )
        if not conversation:
            return

        customer_name = conversation.customer_name or ""
        graph = websocket.app.state.agent_graph
        manager = ChatWebSocketManager()

        await manager.connect(websocket, conversation_id)
        try:
            while True:
                data = await websocket.receive_json()
                await manager.handle_message(
                    conversation_id=conversation_id,
                    business_id=business_id,
                    customer_name=customer_name,
                    existing_proposal_id=existing_proposal_id,
                    data=data,
                    db=self.db,
                    graph=graph,
                )
        except WebSocketDisconnect:
            logger.info(f"[conversation={conversation_id}] Client disconnected")
        except Exception:
            logger.exception(f"[conversation={conversation_id}] Unexpected WebSocket error")
        finally:
            manager.disconnect(conversation_id)

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    def _decode_conv_cursor(
        self, cursor: Optional[str]
    ) -> tuple[Optional[datetime], Optional[str]]:
        if not cursor:
            return None, None
        try:
            return decode_cursor(cursor)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired cursor.",
            )

    async def _get_or_cache_total(
        self,
        repo: ConversationRepository,
        business_id: str,
        version: str,
        fingerprint: str,
        search: Optional[str],
        started_at_from: Optional[datetime],
        started_at_to: Optional[datetime],
    ) -> int:
        total = await get_cached_count(business_id, version, fingerprint)
        if total is None:
            total = await repo.count_conversations_by_business(
                business_id=business_id,
                search=search,
                started_at_from=started_at_from,
                started_at_to=started_at_to,
            )
            await set_cached_count(business_id, version, fingerprint, total)
        return total

    async def _warm_missing_convs(
        self,
        conv_data_map: dict[str, Optional[dict]],
        repo: ConversationRepository,
    ) -> None:
        """Batch-fetches any conv_ids missing from the individual cache and warms them."""
        missing_ids = [cid for cid, data in conv_data_map.items() if data is None]
        if not missing_ids:
            return
        for entity in await repo.get_by_ids(missing_ids):
            item_dict = ConversationItem.model_validate(
                entity, from_attributes=True
            ).model_dump(mode="json")
            conv_data_map[entity.id] = item_dict
            await set_cached_conversation(entity.id, item_dict)

    async def _conversations_from_page_cache(
        self,
        page_cache: dict,
        repo: ConversationRepository,
        business_id: str,
        version: str,
        fingerprint: str,
        search: Optional[str],
        started_at_from: Optional[datetime],
        started_at_to: Optional[datetime],
        limit: int,
    ) -> ConversationsResponse:
        conv_ids: list[str] = page_cache["conv_ids"]
        next_cursor: Optional[str] = page_cache["next_cursor"]
        has_more: bool = page_cache["has_more"]

        conv_data_map: dict[str, Optional[dict]] = {}
        for conv_id in conv_ids:
            conv_data_map[conv_id] = await get_cached_conversation(conv_id)

        await self._warm_missing_convs(conv_data_map, repo)

        items = [
            ConversationItem.model_validate(conv_data_map[cid])
            for cid in conv_ids
            if conv_data_map.get(cid) is not None
        ]
        total = await self._get_or_cache_total(
            repo, business_id, version, fingerprint, search, started_at_from, started_at_to
        )
        return ConversationsResponse(
            items=items, total=total, has_more=has_more, next_cursor=next_cursor, limit=limit
        )

    async def _conversations_from_db(
        self,
        repo: ConversationRepository,
        business_id: str,
        limit: int,
        sort: Literal["asc", "desc"],
        search: Optional[str],
        started_at_from: Optional[datetime],
        started_at_to: Optional[datetime],
        cursor_ts: Optional[datetime],
        cursor_id: Optional[str],
        version: str,
        fingerprint: str,
        cursor_key: str,
    ) -> ConversationsResponse:
        entities, has_more = await repo.get_conversations_by_business(
            business_id=business_id,
            limit=limit,
            sort=sort,
            search=search,
            started_at_from=started_at_from,
            started_at_to=started_at_to,
            cursor_ts=cursor_ts,
            cursor_id=cursor_id,
        )
        total = await self._get_or_cache_total(
            repo, business_id, version, fingerprint, search, started_at_from, started_at_to
        )
        next_cursor = (
            encode_cursor(entities[-1].started_at, entities[-1].id)
            if has_more and entities
            else None
        )

        conv_ids: list[str] = []
        for entity in entities:
            item_dict = ConversationItem.model_validate(
                entity, from_attributes=True
            ).model_dump(mode="json")
            await set_cached_conversation(entity.id, item_dict)
            conv_ids.append(entity.id)

        await set_cached_page(
            business_id, version, fingerprint, cursor_key, conv_ids, next_cursor, has_more
        )
        return ConversationsResponse(
            items=[ConversationItem.model_validate(e, from_attributes=True) for e in entities],
            total=total,
            has_more=has_more,
            next_cursor=next_cursor,
            limit=limit,
        )

    def _paginate_cursor(
        self,
        messages_asc: list[MessageResponse],
        cursor: Optional[str],
        limit: int,
        order: Literal["asc", "desc"],
        total: int,
    ) -> MessagesResponse:
        """
        Cursor pagination — designed for the chat widget's "load older messages" UX.

        No cursor (initial widget open):
          Returns the last `limit` messages (most recent) so the widget opens at
          the bottom of the conversation.

        With cursor:
          Binary-searches the ascending list for the cursor position (O log n),
          then slices `limit` messages immediately before it (older messages).
          next_cursor in the response points to the oldest item in the batch —
          pass it as ?cursor= to load the next page further back in history.

        Timestamp ties are resolved by a secondary linear scan on message ID within
        the tie bucket (O k, where k ≈ 1 in practice).
        """
        if not cursor:
            # Initial load — tail of the list (most recent messages)
            items = messages_asc[-limit:]
            has_more = total > limit
            next_cursor = encode_cursor(items[0].timestamp, items[0].id) if has_more and items else None
        else:
            try:
                cursor_ts, cursor_id = decode_cursor(cursor)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired cursor.",
                )

            pos = self._find_cursor_pos(messages_asc, cursor_ts, cursor_id)
            # Slice everything before the cursor (older messages)
            slice_start = max(0, pos - limit)
            items = messages_asc[slice_start:pos]
            has_more = slice_start > 0
            next_cursor = (
                encode_cursor(items[0].timestamp, items[0].id)
                if has_more and items
                else None
            )

        if order == "desc":
            items = list(reversed(items))

        return MessagesResponse(
            items=items,
            total=total,
            order=order,
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit,
        )

    async def _validate_connection(
        self,
        websocket: WebSocket,
        business_id: str,
        conversation_id: str,
    ) -> tuple[Optional[ConversationEntity], Optional[str]]:
        """
        Validates the WebSocket connection before accepting it.
        Closes with an RFC 6455 application code on failure so the client can
        distinguish not-found (4004) from forbidden (4003).

        Also loads the existing proposal eagerly so proposal_id is seeded into
        AgentState from DB on every connect — correct even after Redis TTL expiry.
        """
        business = await BusinessRepository(self.db).get_by_id(business_id)
        if not business:
            logger.warning(f"WebSocket rejected — business not found: {business_id}")
            await websocket.close(code=_WS_CLOSE_NOT_FOUND, reason="Business not found")
            return None, None

        conversation = await ConversationRepository(self.db).get_by_id_with_proposal(conversation_id)
        if not conversation:
            logger.warning(f"WebSocket rejected — conversation not found: {conversation_id}")
            await websocket.close(code=_WS_CLOSE_NOT_FOUND, reason="Conversation not found")
            return None, None

        if conversation.business_id != business_id:
            logger.warning(
                f"WebSocket rejected — conversation {conversation_id} "
                f"does not belong to business {business_id}"
            )
            await websocket.close(code=_WS_CLOSE_FORBIDDEN, reason="Forbidden")
            return None, None

        existing_proposal_id: Optional[str] = (
            conversation.proposal.id if conversation.proposal else None
        )
        return conversation, existing_proposal_id

    def _paginate_offset(
        self,
        messages_asc: list[MessageResponse],
        page: int,
        size: int,
        order: Literal["asc", "desc"],
        total: int,
    ) -> MessagesResponse:
        """
        Offset pagination — for the business dashboard where jumping to an
        arbitrary page is required.

        Arithmetic slice from the in-memory list: O(1) index math + O(k) slice
        copy where k = size. Always served from the cache so no DB is touched
        for any page after the first cache miss.
        """
        offset = (page - 1) * size
        items = messages_asc[offset : offset + size]
        pages = max(1, -(-total // size))  # ceiling division

        if order == "desc":
            items = list(reversed(items))

        return MessagesResponse(
            items=items,
            total=total,
            order=order,
            page=page,
            pages=pages,
            size=size,
        )

    @staticmethod
    def _find_cursor_pos(
        messages_asc: list[MessageResponse],
        cursor_ts: datetime,
        cursor_id: str,
    ) -> int:
        """
        Locates the cursor message in a timestamp-sorted list.

        Phase 1 — binary search on timestamp: O(log n).
        Phase 2 — linear scan within the tie bucket to match by ID: O(k), k ≈ 1.

        Returns the index of the cursor message, or the nearest timestamp
        position if the message was deleted / not found (stale cursor).
        """
        timestamps = [m.timestamp for m in messages_asc]
        lo = bisect_left(timestamps, cursor_ts)

        # Walk forward within the timestamp bucket to find the exact message
        pos = lo
        while pos < len(messages_asc):
            if messages_asc[pos].id == cursor_id:
                return pos
            if messages_asc[pos].timestamp > cursor_ts:
                break  # exited the bucket — cursor not found (deleted/stale)
            pos += 1

        return lo  # best-effort fallback: use the timestamp boundary