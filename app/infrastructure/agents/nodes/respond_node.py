import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.agents.llm import get_chat_llm
from app.infrastructure.prompts.proposal_prompts import (
    CLARIFY_SECTION,
    EDIT_PROPOSAL_SECTION,
    MATCHED_SERVICES_SECTION,
    PROPOSAL_GENERATED_SECTION,
    RAG_CONTEXT_SECTION,
    RESPOND_SYSTEM_PROMPT,
)
from app.infrastructure.repository.business_repository import BusinessRepository

logger = logging.getLogger(__name__)

_INTERNAL_SERVICE_FIELDS = {"relevance_score"}


def _format_services_for_prompt(matched_services: list[dict]) -> str:
    clean = [{k: v for k, v in s.items() if k not in _INTERNAL_SERVICE_FIELDS} for s in matched_services]
    return json.dumps(clean, indent=2)


def _build_system_prompt(
    business_name: str,
    intent: str,
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

    # Clarify section: agent should ask requirements-gathering questions
    clarify_section = CLARIFY_SECTION if intent == "clarify" else ""

    # Proposal sections: only one fires at a time, only when proposal_node just ran
    proposal_section = ""
    edit_proposal_section = ""
    if proposal_generated and proposal_id:
        if intent == "edit_proposal":
            edit_proposal_section = EDIT_PROPOSAL_SECTION.format(proposal_id=proposal_id)
        else:
            proposal_section = PROPOSAL_GENERATED_SECTION.format(proposal_id=proposal_id)

    return RESPOND_SYSTEM_PROMPT.format(
        business_name=business_name,
        rag_section=rag_section,
        matched_services_section=matched_services_section,
        clarify_section=clarify_section,
        proposal_section=proposal_section,
        edit_proposal_section=edit_proposal_section,
    )


async def respond_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Generates the final streaming response.

    The system prompt is built dynamically based on intent so the agent's tone
    and instructions match exactly what happened this turn:
      - "rag"          → answer and guide naturally
      - "clarify"      → ask 2-3 targeted requirements questions
      - "proposal"     → confirm the new proposal was created
      - "edit_proposal"→ confirm what changed and what stayed the same
    """
    db: AsyncSession = config["configurable"]["db"]

    business_name = state["business_id"]
    try:
        business = config["configurable"].get("business") or await BusinessRepository(db).get_by_id(state["business_id"])
        if business:
            business_name = business.name
    except Exception:
        logger.exception(f"[conversation={state['conversation_id']}] Failed to load business name")

    system_prompt = _build_system_prompt(
        business_name=business_name,
        intent=state.get("intent", "rag"),
        retrieved_chunks=state["retrieved_chunks"],
        matched_services=state.get("matched_services", []),
        proposal_generated=state.get("proposal_generated", False),
        proposal_id=state.get("proposal_id"),
    )

    llm = get_chat_llm(temperature=0.7, streaming=True)

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
