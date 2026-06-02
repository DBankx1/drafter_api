import logging

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.cache.message_cache import invalidate_messages
from app.infrastructure.repository.message_repository import MessageRepository
from app.models.enums.chat_roles import ChatRoles

logger = logging.getLogger(__name__)


async def memory_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Persists the completed turn to Postgres (long-term memory) and invalidates
    the message list cache so the next API read returns fresh data.

    Runs after respond_node so a DB failure never blocks or re-triggers generation.
    Redis short-term memory is handled automatically by the LangGraph checkpointer.

    Cache invalidation is write-through: any successful DB write is immediately
    followed by a cache delete. The cache TTL (5 min) is a safety net only.
    """
    db: AsyncSession = config["configurable"]["db"]
    conv_id = state["conversation_id"]

    token_count: int | None = None
    if state["messages"]:
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and hasattr(last_msg, "usage_metadata") and last_msg.usage_metadata:
            token_count = last_msg.usage_metadata.get("output_tokens")

    try:
        message_repo = MessageRepository(db)

        await message_repo.create(
            conversation_id=conv_id,
            role=ChatRoles.USER,
            content=state["user_message"],
            intent=state["intent"],
            meta={"retrieved_chunk_count": len(state["retrieved_chunks"])},
        )

        await message_repo.create(
            conversation_id=conv_id,
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
        logger.exception(f"[conversation={conv_id}] Failed to persist messages to Postgres")
        # Do not invalidate cache if DB write failed — cache still reflects reality
        return {}

    # Write-through invalidation: DB is updated, cache must be cleared
    await invalidate_messages(conv_id)

    return {}
