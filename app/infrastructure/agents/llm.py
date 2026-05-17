from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from app.core.config import settings


def _make_llm(model: str, temperature: float, streaming: bool = False) -> ChatOpenAI:
    """
    Base factory. Every reliability knob lives here — one place to update for all nodes.

    max_retries: OpenAI client retries with exponential backoff on 429/5xx before the LangChain fallback chain is ever tried. This handles transient blips without degrading to a cheaper model.

    request_timeout: Bounds per-request latency. Without this, a hung OpenAI connection stalls the WebSocket indefinitely.
    """
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        streaming=streaming,
        api_key=settings.OPENAI_API_KEY,
        max_retries=settings.LLM_MAX_RETRIES,
        request_timeout=settings.LLM_REQUEST_TIMEOUT,
    )


def build_with_fallback(
    primary_model: str,
    fallback_model: str,
    temperature: float,
    streaming: bool = False,
    output_schema: type | None = None,
) -> Runnable:
    """
    Wires a primary + fallback model into a single Runnable.

    Schema is applied to BOTH models before .with_fallbacks() so both branches return
    the same type. If the schema were applied after, the fallback branch would return a
    raw AIMessage instead of the Pydantic model, causing a runtime type error.

    Failure path per request:
      1. Primary model → up to max_retries with backoff (OpenAI client)
      2. All retries exhausted → LangChain tries fallback model
      3. Fallback also fails → raises, caught by each node's try/except
    """
    primary = _make_llm(primary_model, temperature, streaming)
    fallback = _make_llm(fallback_model, temperature, streaming)

    if output_schema:
        return primary.with_structured_output(output_schema).with_fallbacks(
            [fallback.with_structured_output(output_schema)]
        )
    return primary.with_fallbacks([fallback])


def get_chat_llm(
    temperature: float = 0.7,
    streaming: bool = False,
    output_schema: type | None = None,
) -> Runnable:
    """
    Cheap, fast model for classification and conversational responses.
    Optimises cost on the high-frequency path (every message triggers this).
    """
    return build_with_fallback(
        primary_model=settings.CHAT_MODEL,
        fallback_model=settings.CHAT_FALLBACK_MODEL,
        temperature=temperature,
        streaming=streaming,
        output_schema=output_schema,
    )


def get_proposal_llm(output_schema: type | None = None) -> Runnable:
    """
    High-quality model for proposal generation — the final customer-facing deliverable.
    Falls back to the chat model if the primary is unavailable: a lower-quality proposal
    is better than a failed request mid-conversation.
    """
    return build_with_fallback(
        primary_model=settings.PROPOSAL_MODEL,
        fallback_model=settings.PROPOSAL_FALLBACK_MODEL,
        temperature=0.2,
        output_schema=output_schema,
    )
