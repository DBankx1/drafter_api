import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity.knowledge_base import DocumentChunk
from app.models.enums.knowledge_base_type import KnowledgeBaseStatus, KnowledgeBaseType
from app.infrastructure.repository.knowledge_base.knowledge_base_repository import KnowledgeBaseRepository
from app.infrastructure.repository.knowledge_base.document_chunk_repository import DocumentChunkRepository
from app.services.knowledge_base.chunker import Chunker
from app.services.knowledge_base.embedder import Embedder
from app.services.knowledge_base.parsers.pdf_parser import PdfParser
from app.services.knowledge_base.parsers.url_parser import UrlParser

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Orchestrates the full pipeline:
    Raw source → Parse → Chunk → Embed → Store

    One instance per ingestion job. Stateless beyond its dependencies.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.kb_repo = KnowledgeBaseRepository(db)
        self.chunk_repo = DocumentChunkRepository(db)
        self.chunker = Chunker(chunk_size=512, chunk_overlap=100)
        self.embedder = Embedder()

    async def ingest(self, kb_id: str, business_id: str) -> None:
        logger.info(f"Starting ingestion: kb_id={kb_id} business_id={business_id}")

        await self.kb_repo.update_status(kb_id, KnowledgeBaseStatus.PENDING)

        try:
            kb = await self.kb_repo.get_by_id(kb_id)
            if not kb:
                raise ValueError(f"KnowledgeBase {kb_id} not found")

            chunks_text = await self._parse_and_chunk(kb)

            if not chunks_text:
                logger.warning(f"No chunks produced for kb_id={kb_id} — source may be empty")
                await self.kb_repo.update_status(kb_id, KnowledgeBaseStatus.ERROR)
                return

            logger.info(f"Embedding {len(chunks_text)} chunks for kb_id={kb_id}")
            embedded_chunks = await self.embedder.embed_chunks(chunks_text)


            chunk_entities = [
                DocumentChunk(
                    business_id=business_id,
                    source_id=kb_id,
                    content=chunk.content,
                    embedding=chunk.embedding,
                    chunk_index=chunk.chunk_index,
                    meta=chunk.metadata,
                )
                for chunk in embedded_chunks
            ]

            await self.chunk_repo.insert_chunks(chunk_entities)

            await self.kb_repo.update_status(
                kb_id,
                KnowledgeBaseStatus.PROCESSED,
                chunk_count=len(chunk_entities),
            )

            logger.info(f"Ingestion complete: kb_id={kb_id} — {len(chunk_entities)} chunks stored")

        except Exception as e:
            logger.exception(f"Ingestion failed: kb_id={kb_id} error={e}")
            await self.kb_repo.update_status(kb_id, KnowledgeBaseStatus.ERROR)
            raise

    async def _parse_and_chunk(self, kb) -> list:
        """
        Routes to the right parser and returns TextChunks.
        Adding a new source type = add a new branch here.
        """
        source_type = kb.source_type
        
        match source_type:
            case KnowledgeBaseType.PDF:
                file_bytes = await get_file_bytes(kb.source_reference)
                parser = PdfParser()
                pages = parser.parse(file_bytes)
                return self.chunker.chunk_documents([
                    {"text": p.text, "page_num": p.page_num, "source_type": "pdf"}
                    for p in pages
                ])
            
            case KnowledgeBaseType.URL:
                parser = UrlParser()
                text = await parser.parse(kb.source_reference)
                return self.chunker.chunk(text, base_metadata={
                    "source_type": "url",
                    "url": kb.source_reference,
                })
            
            case KnowledgeBaseType.TEXT:
                return self.chunker.chunk(kb.source_reference, base_metadata={
                    "source_type": "text",
                })
            
            case _:
                raise ValueError(f"Unsupported source type: {source_type}")