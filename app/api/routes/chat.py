from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.orm import Session
from app.infrastructure.database.db import get_db
from app.services.chat.chat_service import ChatService

router = APIRouter(tags=["chat"], prefix="/chat")

@router.websocket("/ws/{business_id}/{conversation_id}")
async def chat(websocket: WebSocket, business_id: str, conversation_id: str, db: Session = Depends(get_db)):
    chat_service = ChatService(websocket, business_id, conversation_id, db)
    await chat_service.handle_chat_message()