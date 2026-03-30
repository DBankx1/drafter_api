
from fastapi import Depends, UploadFile
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middlewares.auth import get_current_user
from app.core.middlewares.business_auth import get_user_business
from app.infrastructure.database.db import get_db
from app.models.dto.auth import TokenPayload
from app.models.dto.knowledge_base import KnowledgeBaseResponse
from app.models.entity.business import BusinessEntity
from app.services.knowledge_base.knowledge_base_service import KnowledgeBaseService

router = APIRouter(tags=["knowledge_base"], prefix="/knowledge-base")

@router.post("/upload/pdf")
async def upload_knowledge_base(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business)
) -> KnowledgeBaseResponse:
    """Endpoint to upload a knowledge base file."""
    
    service = KnowledgeBaseService(db)
    return await service.upload_pdf_knowledge_base(business.id, file)
    
    
