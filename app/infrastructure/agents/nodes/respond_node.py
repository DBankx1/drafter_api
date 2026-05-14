import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.prompts.proposal_prompts import (
    MATCHED_SERVICES_SECTION,
    PROPOSAL_GENERATED_SECTION,
    RAG_CONTEXT_SECTION,
    RESPOND_SYSTEM_PROMPT,
)
from app.infrastructure.repository.business_repository import BusinessRepository

logger = logging.getLogger(__name__)

# Fields added by rag_node for internal use — strip before sending to the LLM
_INTERNAL_SERVICE_FIELDS = {"relevance_score"}


def _format_services_for_prompt(matched_services: list[dict]) -> str:
    """Strips internal bookkeeping fields so the LLM only sees clean service data."""
    clean = [{k: v for k, v in s.items() if k not in _INTERNAL_SERVICE_FIELDS} for s in matched_services]
    return json.dumps(clean, indent=2)


def _build_system_prompt(
    business_name: str,
    retrieved_chunks: list[str],
    matched_services: list[dict],
    proposal_generated: bool,
    proposal_id: str | None,
) -> str:
    rag_section = ""
    if retrieved_chunks:
        rag_section = RAG_CONTEXT_SECTION.format(chunks="\n\n---\n\n".join(retrieved_chunks))

    matched_services_section = ""
    if matched_services:
        matched_services_section = MATCHED_SERVICES_SECTION.format(
            services=_format_services_for_prompt(matched_services)
        )

    proposal_section = ""
    if proposal_generated and proposal_id:
        proposal_section = PROPOSAL_GENERATED_SECTION.format(proposal_id=proposal_id)

    return RESPOND_SYSTEM_PROMPT.format(
        business_name=business_name,
        rag_section=rag_section,
        matched_services_section=matched_services_section,
        proposal_section=proposal_section,
    )


async def respond_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Generates the final streaming response to the customer.

    streaming=True on the LLM enables per-token events when the caller uses
    graph.astream_events() — the WebSocket layer intercepts those events and
    forwards tokens in real time. This node itself uses ainvoke (collects full
    response) so state is updated cleanly after generation.
    """
    db: AsyncSession = config["configurable"]["db"]

    # proposal_node (when it ran) already fetched and cached business — avoid a second query
    business_name = state["business_id"]
    try:
        business = config["configurable"].get("business") or await BusinessRepository(db).get_by_id(state["business_id"])
        if business:
            business_name = business.name
    except Exception:
        logger.exception(f"[conversation={state['conversation_id']}] Failed to load business name")

    system_prompt = _build_system_prompt(
        business_name=business_name,
        retrieved_chunks=state["retrieved_chunks"],
        matched_services=state.get("matched_services", []),
        proposal_generated=state.get("proposal_generated", False),
        proposal_id=state.get("proposal_id"),
    )

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.7,
        streaming=True,
        api_key=settings.OPENAI_API_KEY,
    )

    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"],
        HumanMessage(content=state["user_message"]),
    ]

    try:
        ai_message: AIMessage = await llm.ainvoke(messages)
    except Exception:
        logger.exception(f"[conversation={state['conversation_id']}] LLM call failed")
        ai_message = AIMessage(content="I'm sorry, I encountered an error. Please try again.")

    return {
        "messages": [HumanMessage(content=state["user_message"]), ai_message],
        "response_text": ai_message.content,
    }
