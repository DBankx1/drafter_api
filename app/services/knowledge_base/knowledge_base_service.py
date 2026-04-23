
import asyncio
import logging
from os import name

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.validators.files.pdf_validator import PDFValidator
from app.infrastructure.repository.knowledge_base.document_chunk_repository import DocumentChunkRepository
from app.infrastructure.repository.knowledge_base.knowledge_base_repository import KnowledgeBaseRepository
from app.infrastructure.supabase.storage import SupabaseStorage
from app.models.dto.knowledge_base import KnowledgeBaseResponse, TextKnowledgeBaseCreate, URLKnowledgeBaseCreate
from app.models.enums.knowledge_base_type import KnowledgeBaseStatus, KnowledgeBaseType
from app.infrastructure.workers.tasks.knowledge_base_injestion_task import ingest_knowledge_base

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    """
    Service layer for knowledge base operations.
    Handles business logic related to knowledge bases.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.kb_repo = KnowledgeBaseRepository(db)
        self.storage = SupabaseStorage()
        self.chunk_repo = DocumentChunkRepository(db)
        
    
    async def upload_pdf_knowledge_base(self, business_id: str, file: UploadFile) -> KnowledgeBaseResponse:
        """Handles the entire flow of uploading a PDF knowledge base"""
        
        file_bytes = await PDFValidator.validate(file)
        
        logger.info(
            f"PDF validated: filename={file.filename} "
            f"size={len(file_bytes) / 1024:.1f}KB "
            f"business_id={business_id}"
        )
        
        kb = await self.kb_repo.create(business_id=business_id, source_type=KnowledgeBaseType.PDF, source_reference="", meta={"original_filename": file.filename}, name=file.filename, kb_size=len(file_bytes))
        
        storage_path = self.storage.build_path(business_id, file.filename) # type: ignore
        
        upload_task = asyncio.to_thread(self.storage.upload_file, storage_path, file_bytes)
        
        reference_task = self.kb_repo.update(id=kb.id, source_reference=storage_path)
        
        try:
            await asyncio.gather(upload_task, reference_task)
        except Exception as e:
            # If either fails, mark as failed and clean up
            logger.exception(f"Upload failed for kb_id={kb.id}: {e}")
            await self.kb_repo.update_status(kb.id, KnowledgeBaseStatus.ERROR)
            await self._cleanup_storage(storage_path)
            raise
        
        logger.info(f"Upload complete: kb_id={kb.id} path={storage_path}")
        
        task = ingest_knowledge_base.delay(
            kb_id=kb.id,
            business_id=business_id,
        )
        
        logger.info(f"Ingestion task queued: task_id={task.id} kb_id={kb.id}")
        
        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            kb_size=kb.kb_size,
            business_id=kb.business_id,
            source_type=kb.source_type,
            source_reference=storage_path,
            status=kb.status,
            meta=kb.meta,
            uploaded_at=kb.uploaded_at
        )
    
    async def upload_text_knowledge_base(self, business_id: str, data: TextKnowledgeBaseCreate) -> KnowledgeBaseResponse:
        """Handles the flow of uploading a text-based knowledge base"""
        
        kb = await self.kb_repo.create(business_id=business_id, source_type=KnowledgeBaseType.TEXT, source_reference=data.content, meta={}, name=data.label, kb_size=len(data.content))
        
        logger.info(f"Text KB created: kb_id={kb.id} business_id={business_id}")
        
        task = ingest_knowledge_base.delay(
            kb_id=kb.id,
            business_id=business_id,
        )
        
        logger.info(f"Ingestion task queued: task_id={task.id} kb_id={kb.id}")
        
        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            kb_size=kb.kb_size,
            business_id=kb.business_id,
            source_type=kb.source_type,
            source_reference=kb.source_reference,
            status=kb.status,
            meta=kb.meta,
            uploaded_at=kb.uploaded_at
        )
    
    async def upload_url_knowledge_base(self, business_id: str, data: URLKnowledgeBaseCreate) -> KnowledgeBaseResponse:
        """Handles the flow of uploading a knowledge base from a URL"""
        
        kb = await self.kb_repo.create(business_id=business_id, source_type=KnowledgeBaseType.URL, source_reference=data.url, meta={}, name=data.label, kb_size=0)
        
        logger.info(f"URL KB created: kb_id={kb.id} business_id={business_id} url={data.url}")
        
        task = ingest_knowledge_base.delay(
            kb_id=kb.id,
            business_id=business_id,
        )
        
        logger.info(f"Ingestion task queued: task_id={task.id} kb_id={kb.id}")
        
        return KnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            kb_size=kb.kb_size,
            business_id=kb.business_id,
            source_type=kb.source_type,
            source_reference=kb.source_reference,
            status=kb.status,
            meta=kb.meta,
            uploaded_at=kb.uploaded_at
        )
    
    async def get_knowledge_bases(self, business_id: str) -> list[KnowledgeBaseResponse]:
        """Retrieves all knowledge bases for a given business."""
        kbs = await self.kb_repo.get_all_by_business(business_id)
        return [
            KnowledgeBaseResponse(
                id=kb.id,
                name=kb.name,
                kb_size=kb.kb_size,
                business_id=kb.business_id,
                source_type=kb.source_type,
                source_reference=kb.source_reference,
                status=kb.status,
                meta=kb.meta,
                uploaded_at=kb.uploaded_at
            )
            for kb in kbs
        ]
    
    async def view_knowledge_base_file(self, business_id: str, kb_id: str) -> str:
        """Retrieves a knowledge base file Url for viewing/downloading."""
        kb = await self.kb_repo.get_by_id(kb_id)
        if not kb or kb.business_id != business_id:
            raise ValueError("Knowledge base not found")
        if kb.source_type == KnowledgeBaseType.PDF:
            url = self.storage.get_signed_url(kb.source_reference)
            return url
        else:
            raise ValueError("Viewing is only supported for PDF knowledge bases")
        
    async def delete_knowledge_base(self, business_id: str, kb_id: str) -> None:
        """Deletes a knowledge base and its associated file if applicable."""
        kb = await self.kb_repo.get_by_id(kb_id)
        if not kb or kb.business_id != business_id:
            raise ValueError("Knowledge base not found")
        
        await self.chunk_repo.delete_by_source(kb_id)
        
        await self.kb_repo.delete(kb_id, business_id)
        logger.info(f"Knowledge base deleted from DB: kb_id={kb_id}")
        
        if kb.source_type == KnowledgeBaseType.PDF and kb.source_reference:
            await self._cleanup_storage(kb.source_reference)
            logger.info(f"Knowledge base file deleted from storage: path={kb.source_reference}")
    
    async def _cleanup_storage(self, path: str) -> None:
        """Best-effort storage cleanup on failure — never raises."""
        try:
            await asyncio.to_thread(self.storage.delete_file, path)
        except Exception:
            logger.warning(f"Cleanup failed for path={path} — may need manual removal")
    
