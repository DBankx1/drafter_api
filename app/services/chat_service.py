import logging

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repository.business_repository import BusinessRepository
from app.infrastructure.repository.conversation_repository import ConversationRepository
from app.infrastructure.websockets.chat_socket_manager import ChatWebSocketManager
from app.models.entity.conversation import ConversationEntity

logger = logging.getLogger(__name__)

# WebSocket close codes (4000–4999 are application-defined per RFC 6455)
_WS_CLOSE_NOT_FOUND = 4004
_WS_CLOSE_FORBIDDEN = 4003


class ChatService:
    def __init__(
        self,
        websocket: WebSocket,
        business_id: str,
        conversation_id: str,
        db: AsyncSession,
    ) -> None:
        self.websocket = websocket
        self.business_id = business_id
        self.conversation_id = conversation_id
        self.db = db
        self.manager = ChatWebSocketManager()
        # WebSocket exposes .app via its ASGI scope — no need to inject Request
        self.graph = websocket.app.state.agent_graph

    async def handle_chat_message(self) -> None:
        conversation = await self._validate_connection()
        if not conversation:
            return

        customer_name = conversation.customer_name or ""

        await self.manager.connect(self.websocket, self.conversation_id)
        try:
            while True:
                data = await self.websocket.receive_json()
                await self.manager.handle_message(
                    conversation_id=self.conversation_id,
                    business_id=self.business_id,
                    customer_name=customer_name,
                    data=data,
                    db=self.db,
                    graph=self.graph,
                )
        except WebSocketDisconnect:
            logger.info(f"[conversation={self.conversation_id}] Client disconnected")
        except Exception:
            logger.exception(f"[conversation={self.conversation_id}] Unexpected WebSocket error")
        finally:
            self.manager.disconnect(self.conversation_id)

    async def _validate_connection(self) -> ConversationEntity | None:
        """
        Validates the business and conversation before accepting the socket.
        Rejects with an application close code on failure so the client can
        distinguish 'not found' from a server crash.
        """
        business = await BusinessRepository(self.db).get_by_id(self.business_id)
        if not business:
            logger.warning(f"WebSocket rejected — business not found: {self.business_id}")
            await self.websocket.close(code=_WS_CLOSE_NOT_FOUND, reason="Business not found")
            return None

        conversation = await ConversationRepository(self.db).get_by_id(self.conversation_id)
        if not conversation:
            logger.warning(f"WebSocket rejected — conversation not found: {self.conversation_id}")
            await self.websocket.close(code=_WS_CLOSE_NOT_FOUND, reason="Conversation not found")
            return None

        # Tenant isolation: conversation must belong to the business in the URL
        if conversation.business_id != self.business_id:
            logger.warning(
                f"WebSocket rejected — conversation {self.conversation_id} "
                f"does not belong to business {self.business_id}"
            )
            await self.websocket.close(code=_WS_CLOSE_FORBIDDEN, reason="Forbidden")
            return None

        return conversation
