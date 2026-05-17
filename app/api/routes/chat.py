import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.db import get_db
from app.infrastructure.repository.business_repository import BusinessRepository
from app.infrastructure.repository.conversation_repository import ConversationRepository
from app.models.dto.chat import StartConversationRequest, StartConversationResponse
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"], prefix="/chat")
logger = logging.getLogger(__name__)

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/conversations/{business_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation",
    description="Called by the widget on load to create a conversation before opening the WebSocket.",
)
async def start_conversation(
    business_id: str,
    body: StartConversationRequest,
    db: DbDep,
) -> StartConversationResponse:
    business = await BusinessRepository(db).get_by_id(business_id)
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    conversation = await ConversationRepository(db).create(
        business_id=business_id,
        customer_name=body.customer_name,
        customer_email=body.customer_email,
    )
    return StartConversationResponse(conversation_id=conversation.id)


@router.websocket("/ws/{business_id}/{conversation_id}")
async def chat(
    websocket: WebSocket,
    business_id: str,
    conversation_id: str,
    db: DbDep,
) -> None:
    chat_service = ChatService(websocket, business_id, conversation_id, db)
    await chat_service.handle_chat_message()
