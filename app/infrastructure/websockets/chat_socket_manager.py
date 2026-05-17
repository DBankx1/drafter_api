import logging
from typing import Dict

from fastapi import WebSocket
from langchain_core.messages import AIMessageChunk
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.agents.graph.state import AgentState
from app.models.dto.chat import ChatMessageInput

logger = logging.getLogger(__name__)


class ChatWebSocketManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str) -> None:
        await websocket.accept()
        self.active_connections[conversation_id] = websocket

    def disconnect(self, conversation_id: str) -> None:
        self.active_connections.pop(conversation_id, None)

    async def send_json(self, conversation_id: str, payload: dict) -> None:
        ws = self.active_connections.get(conversation_id)
        if ws:
            await ws.send_json(payload)

    async def handle_message(
        self,
        conversation_id: str,
        business_id: str,
        customer_name: str,
        existing_proposal_id: str | None,
        data: dict,
        db: AsyncSession,
        graph: CompiledStateGraph,
    ) -> None:
        """
        Validates the incoming payload, builds the initial graph state, then
        streams token events back to the WebSocket.

        Protocol (client receives):
          {"type": "token",  "content": "<partial text>"}  — one per streamed token
          {"type": "end"}                                   — turn complete
          {"type": "error", "content": "<message>"}        — validation or runtime error

        The db session is passed via config["configurable"] and never checkpointed
        to Redis — AsyncSession is not JSON-serializable.

        existing_proposal_id is loaded from DB by chat_service on every connect so that
        proposal_id is always correct even after Redis TTL expiry or session reconnect.
        """
        try:
            payload = ChatMessageInput.model_validate(data)
        except ValidationError as exc:
            detail = exc.errors()[0]["msg"] if exc.errors() else "Invalid message"
            await self.send_json(conversation_id, {"type": "error", "content": detail})
            return

        initial_state: AgentState = {
            "business_id": business_id,
            "conversation_id": conversation_id,
            "customer_name": customer_name,
            "user_message": payload.message,
            "intent": "unknown",
            "retrieved_chunks": [],
            "matched_services": [],
            "pricing_config": None,
            "proposal_generated": False,
            "proposal_id": existing_proposal_id,  # DB is source of truth — not Redis alone
            "messages": [],
            "response_text": "",
        }

        config = {
            "configurable": {
                "thread_id": conversation_id,
                "db": db,
            }
        }

        try:
            async for event in graph.astream_events(initial_state, config=config, version="v2"):
                await self._handle_graph_event(conversation_id, event)
        except Exception:
            logger.exception(f"[conversation={conversation_id}] Error during graph stream")
            await self.send_json(
                conversation_id,
                {"type": "error", "content": "Something went wrong. Please try again."},
            )

    async def _handle_graph_event(self, conversation_id: str, event: dict) -> None:
        event_name: str = event.get("event", "")
        event_meta: dict = event.get("metadata", {})

        if event_name == "on_chat_model_stream":
            # Suppress tokens from classify_intent — only forward from respond_node
            if event_meta.get("langgraph_node") == "respond_node":
                chunk: AIMessageChunk = event["data"]["chunk"]
                if chunk.content:
                    await self.send_json(conversation_id, {"type": "token", "content": chunk.content})

        elif event_name == "on_chain_end" and event.get("name") == "memory_node":
            await self.send_json(conversation_id, {"type": "end"})
