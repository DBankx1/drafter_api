from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "drafter_api",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.infrastructure.workers.tasks.knowledge_base_injestion_task"]
)

celery_app.conf.update(
    task_serializer="json",
    result_expires=3600,
)