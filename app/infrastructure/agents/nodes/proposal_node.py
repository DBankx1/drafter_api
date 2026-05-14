import json
import logging
import uuid
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.prompts.proposal_prompts import PROPOSAL_GENERATION_PROMPT
from app.infrastructure.repository.base_repository import BaseRepository
from app.infrastructure.repository.business_repository import BusinessRepository
from app.models.entity.proposal import ProposalEntity
from app.models.enums.proposal_status import ProposalStatus

logger = logging.getLogger(__name__)


class ProposalLineItem(BaseModel):
    service_name: str
    description: str
    quantity: int = 1
    unit_price: float
    total: float


class ProposalOutput(BaseModel):
    title: str
    line_items: list[ProposalLineItem]
    subtotal: float
    notes: str
    next_steps: str


async def proposal_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Generates a structured proposal, persists it to Postgres, and dispatches
    an async Celery notification to the business owner.

    Runs only when classify_intent routes intent == "proposal".
    Has access to RAG context from rag_node (already in state["retrieved_chunks"]).
    Fetches business here (before respond_node) and caches it in config["configurable"]
    so respond_node can reuse it without a second DB query.
    """
    db: AsyncSession = config["configurable"]["db"]

    # Fetch business and cache it — respond_node runs after this and reads from cache
    business_name = state["business_id"]
    try:
        business = await BusinessRepository(db).get_by_id(state["business_id"])
        if business:
            business_name = business.name
            config["configurable"]["business"] = business
    except Exception:
        logger.exception(f"[conversation={state['conversation_id']}] Failed to load business for proposal")

    # rag_node already fetched and stored this in state — reuse it, don't query DB again
    pricing_data = state.get("pricing_config") or {"services": []}

    rag_context = "\n\n".join(state["retrieved_chunks"]) if state["retrieved_chunks"] else "No additional context available."

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.2,
        api_key=settings.OPENAI_API_KEY,
    ).with_structured_output(ProposalOutput)

    prompt_text = PROPOSAL_GENERATION_PROMPT.format(
        business_name=business_name,
        customer_name=state["customer_name"] or "Customer",
        pricing_config=json.dumps(pricing_data, indent=2),
        rag_context=rag_context,
    )

    history_summary = "\n".join(
        f"{m.__class__.__name__}: {m.content}" for m in state["messages"][-6:]
    )

    messages = [
        SystemMessage(content=prompt_text),
        HumanMessage(content=f"Conversation so far:\n{history_summary}\n\nLatest message: {state['user_message']}"),
    ]

    proposal_output: Optional[ProposalOutput] = None
    try:
        proposal_output = await llm.ainvoke(messages)
    except Exception:
        logger.exception(f"[conversation={state['conversation_id']}] Proposal generation LLM call failed")

    proposal_id: Optional[str] = None

    if proposal_output:
        try:
            proposal_id = str(uuid.uuid4())
            proposal_repo = BaseRepository(ProposalEntity, db)
            await proposal_repo.create(
                id=proposal_id,
                conversation_id=state["conversation_id"],
                content_json=proposal_output.model_dump(),
                status=ProposalStatus.DRAFT,
            )

            # Fire-and-forget Celery notification — non-blocking
            try:
                from app.infrastructure.workers.tasks.proposal_notification_task import notify_business_of_proposal
                notify_business_of_proposal.delay(
                    business_id=state["business_id"],
                    proposal_id=proposal_id,
                    conversation_id=state["conversation_id"],
                )
            except Exception:
                logger.exception("Failed to enqueue proposal notification — proposal was still saved")

        except Exception:
            logger.exception(f"[conversation={state['conversation_id']}] Failed to persist proposal")
            proposal_id = None

    logger.info(f"[conversation={state['conversation_id']}] proposal_id={proposal_id}")
    return {
        "proposal_generated": proposal_id is not None,
        "proposal_id": proposal_id,
    }
