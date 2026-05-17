import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.agents.llm import get_chat_llm
from app.infrastructure.prompts.proposal_prompts import INTENT_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)


class IntentClassification(BaseModel):
    reasoning: str  # chain-of-thought: forces the LLM to justify before labelling
    intent: Literal["rag", "clarify", "proposal", "edit_proposal"]


async def classify_intent(state: AgentState) -> dict:
    """
    Routes the conversation into one of four intents.

    Uses the full message history so context-dependent messages ("yes, go ahead",
    "change the timeline") are classified correctly.

    The `reasoning` field is a chain-of-thought trick — the LLM must justify its
    label before committing. This significantly reduces misclassification on borderline
    cases like "I want a quote" (clarify, not proposal) and "remove the SEO package"
    (edit_proposal, only when a proposal already exists). Reasoning is logged for
    observability but never stored.
    """
    has_existing_proposal = state.get("proposal_id") is not None

    llm = get_chat_llm(temperature=0, output_schema=IntentClassification)

    system_prompt = INTENT_CLASSIFICATION_PROMPT.format(
        has_existing_proposal=str(has_existing_proposal).lower()
    )

    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"],
        HumanMessage(content=state["user_message"]),
    ]

    try:
        result: IntentClassification = await llm.ainvoke(messages)
        intent = result.intent
        logger.info(
            f"[conversation={state['conversation_id']}] intent={intent} | reasoning: {result.reasoning}"
        )
    except Exception:
        logger.exception("Intent classification failed, defaulting to 'rag'")
        intent = "rag"

    return {"intent": intent}
