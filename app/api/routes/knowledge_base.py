
from fastapi import Depends, UploadFile
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middlewares.auth import get_current_user
from app.core.middlewares.business_auth import get_user_business
from app.infrastructure.database.db import get_db
from app.models.dto.auth import TokenPayload
from app.models.dto.knowledge_base import KnowledgeBaseResponse, TextKnowledgeBaseCreate
from app.models.entity.business import BusinessEntity
from app.services.knowledge_base.knowledge_base_service import KnowledgeBaseService

router = APIRouter(tags=["knowledge_base"], prefix="/knowledge-base")

@router.post("/upload/pdf")
async def upload_pdf_knowledge_base(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business)
) -> KnowledgeBaseResponse:
    """Endpoint to upload PDF knowledge base file."""
    
    service = KnowledgeBaseService(db)
    return await service.upload_pdf_knowledge_base(business.id, file)

@router.post('/upload/txt')
async def upload_txt_knowledge_base(
    data: TextKnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business)
) -> KnowledgeBaseResponse:
    """Endpoint to upload a text-based knowledge base."""
    print(f"This is dataaaa: {data}")
    service = KnowledgeBaseService(db)
    return await service.upload_text_knowledge_base(business.id, data.content)

@router.post('/upload/url')
async def upload_url_knowledge_base(
    url: str,
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business)
) -> KnowledgeBaseResponse:
    """Endpoint to upload a knowledge base from a URL."""
    
    service = KnowledgeBaseService(db)
    return await service.upload_url_knowledge_base(business.id, url)

@router.get("/")
async def get_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business)
) -> list[KnowledgeBaseResponse]:
    """Endpoint to retrieve all knowledge bases for the current business."""
    
    service = KnowledgeBaseService(db)
    return await service.get_knowledge_bases(business.id)    
