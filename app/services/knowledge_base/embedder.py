import asyncio
from openai import AsyncOpenAI
from app.core.config import settings
from app.services.knowledge_base.chunker import TextChunk
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmbeddedChunk:
    content: str
    embedding: list[float]
    chunk_index: int
    metadata: dict


class Embedder:
    """
    Converts TextChunks into EmbeddedChunks using OpenAI's embedding API.
    Batches requests to stay within API rate limits and minimize latency.
    """
    
    BATCH_SIZE = 100

    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIM  

    async def embed_chunks(self, chunks: list[TextChunk]) -> list[EmbeddedChunk]:
        """
        Embed all chunks, batching requests to avoid rate limits.
        Preserves original order — critical so chunk_index stays accurate.
        """
        if not chunks:
            return []

        batches = self._make_batches(chunks)
        embedded_batches = await asyncio.gather(
            *[self._embed_batch(batch) for batch in batches]
        )

        # Flatten batches back into a single ordered list
        return [chunk for batch in embedded_batches for chunk in batch]

    async def embed_query(self, query: str) -> list[float]:
        """
        Embed a single search query at retrieval time.
        Must use the same model as ingestion — dimensions must match pgvector column.
        """
        response = await self._client.embeddings.create(
            input=query.strip(),
            model=self._model,
            dimensions=self._dimensions,
        )
        return response.data[0].embedding

    async def _embed_batch(self, chunks: list[TextChunk]) -> list[EmbeddedChunk]:
        texts = [chunk.content for chunk in chunks]

        logger.info(f"Embedding batch of {len(texts)} chunks")

        response = await self._client.embeddings.create(
            input=texts,
            model=self._model,
            dimensions=self._dimensions,
        )

        return [
            EmbeddedChunk(
                content=chunk.content,
                embedding=data.embedding,
                chunk_index=chunk.chunk_index,
                metadata=chunk.metadata,
            )
            for chunk, data in zip(chunks, response.data)
        ]

    def _make_batches(self, chunks: list[TextChunk]) -> list[list[TextChunk]]:
        return [
            chunks[i : i + self.BATCH_SIZE]
            for i in range(0, len(chunks), self.BATCH_SIZE)
        ]