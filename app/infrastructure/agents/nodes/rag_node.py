import asyncio
import logging

import numpy as np
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.agents.graph.state import AgentState
from app.infrastructure.repository.knowledge_base.document_chunk_repository import DocumentChunkRepository
from app.infrastructure.repository.pricing_config_repository import PricingConfigRepository
from app.services.knowledge_base.embedder import Embedder

logger = logging.getLogger(__name__)

# Cosine similarity threshold for a service to be considered relevant.
# OpenAI text-embedding-3-small: ~0.35 reliably filters unrelated content.
_SERVICE_RELEVANCE_THRESHOLD = 0.35


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / norm) if norm > 0 else 0.0


async def _match_pricing_services(
    query_embedding: list[float],
    services: list[dict],
    embedder: Embedder,
) -> list[dict]:
    """
    Returns the subset of services that are semantically relevant to the query,
    ranked by cosine similarity. Reuses the query embedding already computed for
    the vector search — no extra embedding API call for the query itself.

    Service texts are embedded as a single batch (pricing configs are small,
    typically < 10 services) so the overhead is one lightweight API call.
    """
    if not services:
        return []

    # Build a descriptive text per service so the embedding captures both name + context
    service_texts = [
        f"{s['name']}: {s.get('description', '')}".strip(": ")
        for s in services
    ]

    service_embeddings = await embedder.embed_texts(service_texts)

    matched = []
    for service, s_emb in zip(services, service_embeddings):
        score = _cosine_similarity(query_embedding, s_emb)
        if score >= _SERVICE_RELEVANCE_THRESHOLD:
            matched.append({**service, "relevance_score": round(score, 4)})

    matched.sort(key=lambda s: s["relevance_score"], reverse=True)
    return matched


async def rag_node(state: AgentState, config: RunnableConfig) -> dict:
    """
    Retrieves context for both RAG and proposal paths in two parallel phases.

    Phase 1 — concurrent:
        embed_query        → produces the query vector
        fetch_pricing      → loads the business's service catalogue from DB

    Phase 2 — concurrent (both depend on phase 1 results):
        vector_search      → pgvector similarity search against document chunks
        match_services     → cosine similarity between query vector and service texts

    The query embedding is computed once and reused for both vector search and
    service matching, avoiding a redundant API call. The pricing config is fetched
    once here and stored in state so proposal_node doesn't need to query DB again.
    """
    db: AsyncSession = config["configurable"]["db"]
    embedder = Embedder()

    retrieved_chunks: list[str] = []
    matched_services: list[dict] = []
    pricing_config: dict | None = None

    try:
        # Phase 1: embed the query and fetch pricing in parallel
        query_embedding, pricing_data = await asyncio.gather(
            embedder.embed_query(state["user_message"]),
            PricingConfigRepository(db).get_services_by_business_id(state["business_id"]),
        )
        pricing_config = pricing_data
        services = pricing_data.get("services", [])

        # Phase 2: vector search + service matching in parallel (both use query_embedding)
        chunks, matched_services = await asyncio.gather(
            DocumentChunkRepository(db).similarity_search(
                query_embedding=query_embedding,
                business_id=state["business_id"],
                top_k=5,
            ),
            _match_pricing_services(query_embedding, services, embedder),
        )
        retrieved_chunks = [c.content for c in chunks]

    except Exception:
        logger.exception(
            f"[conversation={state['conversation_id']}] RAG retrieval failed, continuing with empty context"
        )

    logger.info(
        f"[conversation={state['conversation_id']}] "
        f"chunks={len(retrieved_chunks)} matched_services={len(matched_services)}"
    )
    return {
        "retrieved_chunks": retrieved_chunks,
        "matched_services": matched_services,
        "pricing_config": pricing_config,
    }
