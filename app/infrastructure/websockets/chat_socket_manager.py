from fastapi import WebSocket
from typing import Dict
import json

class ChatWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        self.active_connections[conversation_id] = websocket

    async def disconnect(self, conversation_id: str):
        if conversation_id in self.active_connections:
            del self.active_connections[conversation_id]

    async def send_message(self, conversation_id: str, message: str):
        if conversation_id in self.active_connections:
            websocket = self.active_connections[conversation_id]
            await websocket.send_json(message)
            
    async def handle_message(self, conversation_id: str, data: dict, db):
        # Import here to avoid circular imports
        from agents.proposal_agent import ProposalAgent
        
        ai_agent = ProposalAgent("gpt-4o-mini", db)
        response = await ai_agent.process_message(conversation_id, data)
        await self.send_message(conversation_id, response["content"])