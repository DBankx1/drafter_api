import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.prompts.proposal_prompts import INTENT_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)


class IntentClassification(BaseModel):
    reasoning: str  # chain-of-thought: forces the LLM to justify before labelling
    intent: Literal["rag", "clarify", "proposal", "edit_proposal"]


async def classify_intent(state: AgentState, config: RunnableConfig) -> dict:
    """
    Routes the conversation into one of four intents.

    Uses the full message history so context-dependent messages ("yes, go ahead",
    "change the timeline") are classified correctly.

    The `reasoning` field in the structured output is a chain-of-thought trick —
    asking the LLM to justify before committing to a label improves accuracy on
    borderline cases (e.g. "I want a quote" with no prior requirements = clarify,
    not proposal). The reasoning is logged for observability but not stored.

    Passes state["proposal_id"] to the prompt so the classifier knows whether
    "edit_proposal" is a valid option for this conversation.
    """
    has_existing_proposal = state.get("proposal_id") is not None

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
    ).with_structured_output(IntentClassification)

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
