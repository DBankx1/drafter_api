import logging

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.repository.message_repository import MessageRepository
from app.models.enums.chat_roles import ChatRoles

logger = logging.getLogger(__name__)


async def memory_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Persists the completed turn to Postgres (long-term memory).
    Runs after respond_node so a DB failure never blocks or re-triggers generation.

    Redis short-term memory is handled automatically by the LangGraph checkpointer —
    no explicit Redis writes are needed here.
    """
    db: AsyncSession = config["configurable"]["db"]

    # Extract token count from the last AIMessage in history (populated by respond_node)
    token_count: int | None = None
    if state["messages"]:
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and hasattr(last_msg, "usage_metadata") and last_msg.usage_metadata:
            token_count = last_msg.usage_metadata.get("output_tokens")

    try:
        message_repo = MessageRepository(db)

        await message_repo.create(
            conversation_id=state["conversation_id"],
            role=ChatRoles.USER,
            content=state["user_message"],
            intent=state["intent"],
            meta={"retrieved_chunk_count": len(state["retrieved_chunks"])},
        )

        await message_repo.create(
            conversation_id=state["conversation_id"],
            role=ChatRoles.ASSISTANT,
            content=state["response_text"],
            intent=state["intent"],
            meta={
                "proposal_id": state.get("proposal_id"),
                "proposal_generated": state.get("proposal_generated", False),
            },
            token_count=token_count,
        )
    except Exception:
        logger.exception(
            f"[conversation={state['conversation_id']}] Failed to persist messages to Postgres"
        )

    return {}
