from typing import Annotated, Literal, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    # Identity — set on first turn, restored automatically by Redis checkpoint on subsequent turns
    business_id: str
    conversation_id: str
    customer_name: str

    # Current turn input
    user_message: str

    # Routing — set by classify_intent
    intent: Literal["rag", "proposal", "unknown"]

    # RAG context — always populated by rag_node before branching
    retrieved_chunks: list[str]
    # Pricing services that are semantically relevant to the user's message.
    # Each dict is a ServiceConfig with an added "relevance_score" float.
    matched_services: list[dict]
    # Full pricing config for the business — fetched once in rag_node, reused by proposal_node.
    pricing_config: dict | None

    # Proposal output — set by proposal_node if intent == "proposal"
    proposal_generated: bool
    proposal_id: str | None

    # Conversation history — add_messages reducer append-merges across turns (never overwrites)
    messages: Annotated[list[BaseMessage], add_messages]

    # Final response text — populated by respond_node, consumed by memory_node
    response_text: str
