from fastapi import APIRouter, WebSocket

router = APIRouter(tags=["chat"], prefix="/chat")

@router.websocket("/ws/{business_id}/{conversation_id}")
async def chat(websocket: WebSocket, business_id: str, conversation_id: str):
    await 