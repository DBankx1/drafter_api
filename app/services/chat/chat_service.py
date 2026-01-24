import logging

from fastapi import WebSocket
from app.infrastructure.websockets.chat_socket_manager import ChatWebSocketManager


logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, websocket: WebSocket, business_id: str, conversation_id: str) -> None:
        self.business_id = business_id
        self.conversation_id = conversation_id
        self.websocket = websocket
        self.websocket_manager = ChatWebSocketManager()
        
    async def handle_chat_message(self) -> None:
        try:
            while True:
                data = await self.websocket.receive_json()
                await self.websocket_manager.handle_message(self.conversation_id, data, db)
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
        finally:
            await self.websocket_manager.disconnect(self.conversation_id)