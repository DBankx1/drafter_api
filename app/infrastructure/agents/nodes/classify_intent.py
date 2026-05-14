import logging
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.prompts.proposal_prompts import INTENT_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)


class IntentClassification(BaseModel):
    intent: Literal["rag", "proposal"]


async def classify_intent(state: AgentState, config: RunnableConfig) -> dict:
    """
    Routes the conversation by classifying the customer's intent.

    Uses the full message history so context-dependent messages like
    "yes, send me a quote" are classified correctly.
    """
    # TODO: add LLM model for classification to settings, and experiment with different models
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
    ).with_structured_output(IntentClassification)

    messages = [
        SystemMessage(content=INTENT_CLASSIFICATION_PROMPT),
        *state["messages"],
        HumanMessage(content=state["user_message"]),
    ]

    try:
        result: IntentClassification = await llm.ainvoke(messages)
        intent = result.intent
    except Exception:
        logger.exception("Intent classification failed, defaulting to 'rag'")
        intent = "rag"

    logger.info(f"[conversation={state['conversation_id']}] intent={intent}")
    return {"intent": intent}
