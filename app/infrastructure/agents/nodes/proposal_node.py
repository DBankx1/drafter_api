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
from app.infrastructure.prompts.proposal_prompts import (
    PROPOSAL_EDIT_PROMPT,
    PROPOSAL_GENERATION_PROMPT,
)
from app.infrastructure.repository.business_repository import BusinessRepository
from app.infrastructure.repository.proposal_repository import ProposalRepository
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
    Handles both proposal CREATE and UPDATE in one node.

    CREATE path (intent == "proposal", proposal_id is None):
      Generates a new ProposalOutput from requirements, persists a new ProposalEntity,
      and fires a Celery notification to the business.

    UPDATE path (intent == "edit_proposal", proposal_id is set):
      Loads the existing proposal's content_json, generates an updated ProposalOutput
      that incorporates only the requested changes, and replaces content_json in-place.
      The proposal UUID and all other DB fields are preserved.

    In both paths, fetches business for context and caches it in config["configurable"]
    so respond_node can reuse it without a second DB query.
    """
    db: AsyncSession = config["configurable"]["db"]

    business_name = state["business_id"]
    try:
        business = await BusinessRepository(db).get_by_id(state["business_id"])
        if business:
            business_name = business.name
            config["configurable"]["business"] = business
    except Exception:
        logger.exception(f"[conversation={state['conversation_id']}] Failed to load business")

    pricing_data = state.get("pricing_config") or {"services": []}
    rag_context = "\n\n".join(state["retrieved_chunks"]) if state["retrieved_chunks"] else "No additional context available."

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.2,
        api_key=settings.OPENAI_API_KEY,
    ).with_structured_output(ProposalOutput)

    proposal_repo = ProposalRepository(db)
    is_edit = state["intent"] == "edit_proposal" and state.get("proposal_id") is not None
    proposal_output: Optional[ProposalOutput] = None

    if is_edit:
        proposal_output = await _generate_edit(
            state=state,
            llm=llm,
            business_name=business_name,
            pricing_data=pricing_data,
            rag_context=rag_context,
            proposal_repo=proposal_repo,
        )
    else:
        proposal_output = await _generate_new(
            state=state,
            llm=llm,
            business_name=business_name,
            pricing_data=pricing_data,
            rag_context=rag_context,
        )

    if not proposal_output:
        return {"proposal_generated": False, "proposal_id": state.get("proposal_id")}

    # Persist
    if is_edit:
        proposal_id = state["proposal_id"]
        try:
            await proposal_repo.update_content(proposal_id, proposal_output.model_dump())
            logger.info(f"[conversation={state['conversation_id']}] proposal updated: {proposal_id}")
        except Exception:
            logger.exception(f"[conversation={state['conversation_id']}] Failed to update proposal")
            return {"proposal_generated": False, "proposal_id": proposal_id}
    else:
        proposal_id = str(uuid.uuid4())
        try:
            await proposal_repo.create(
                id=proposal_id,
                conversation_id=state["conversation_id"],
                content_json=proposal_output.model_dump(),
                status=ProposalStatus.DRAFT,
            )
            logger.info(f"[conversation={state['conversation_id']}] proposal created: {proposal_id}")

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
            return {"proposal_generated": False, "proposal_id": None}

    return {"proposal_generated": True, "proposal_id": proposal_id}


async def _generate_new(
    state: AgentState,
    llm,
    business_name: str,
    pricing_data: dict,
    rag_context: str,
) -> Optional[ProposalOutput]:
    history_summary = "\n".join(
        f"{m.__class__.__name__}: {m.content}" for m in state["messages"][-8:]
    )
    prompt_text = PROPOSAL_GENERATION_PROMPT.format(
        business_name=business_name,
        customer_name=state["customer_name"] or "Customer",
        pricing_config=json.dumps(pricing_data, indent=2),
        rag_context=rag_context,
    )
    messages = [
        SystemMessage(content=prompt_text),
        HumanMessage(content=f"Conversation so far:\n{history_summary}\n\nLatest: {state['user_message']}"),
    ]
    try:
        return await llm.ainvoke(messages)
    except Exception:
        logger.exception(f"[conversation={state['conversation_id']}] Proposal generation LLM call failed")
        return None


async def _generate_edit(
    state: AgentState,
    llm,
    business_name: str,
    pricing_data: dict,
    rag_context: str,
    proposal_repo: ProposalRepository,
) -> Optional[ProposalOutput]:
    existing = await proposal_repo.get_by_conversation_id(state["conversation_id"])
    if not existing or not existing.content_json:
        logger.warning(f"[conversation={state['conversation_id']}] Edit requested but no existing proposal found")
        return None

    prompt_text = PROPOSAL_EDIT_PROMPT.format(
        business_name=business_name,
        customer_name=state["customer_name"] or "Customer",
        existing_proposal=json.dumps(existing.content_json, indent=2),
        change_request=state["user_message"],
        pricing_config=json.dumps(pricing_data, indent=2),
        rag_context=rag_context,
    )
    messages = [
        SystemMessage(content=prompt_text),
        HumanMessage(content=state["user_message"]),
    ]
    try:
        return await llm.ainvoke(messages)
    except Exception:
        logger.exception(f"[conversation={state['conversation_id']}] Proposal edit LLM call failed")
        return None
