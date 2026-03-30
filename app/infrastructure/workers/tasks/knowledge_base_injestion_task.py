from celery import Task

from app.core.celery_app import celery_app
from app.infrastructure.database.db import get_db
from app.services.knowledge_base.injestion import IngestionService
import asyncio


class IngestionTask(Task):
    abstract = True
    
@celery_app.task(
    name="knowledge_base_ingestion_task",
    bind=True,
    base=IngestionTask,
    max_retries=3,
    default_retry_delay=60,
)
def ingest_knowledge_base(self, kb_id: str, business_id: str):
    async def _run():
        async with get_db() as db: # type: ignore
            service = IngestionService(db)
            await service.ingest(kb_id, business_id)
    
    try:
        asyncio.run(_run())
    except Exception as exc:
        self.retry(exc=exc)
            
                