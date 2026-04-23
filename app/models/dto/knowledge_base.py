

import datetime

from pydantic import BaseModel

from app.models.enums.knowledge_base_type import KnowledgeBaseStatus, KnowledgeBaseType


class KnowlegeBase(BaseModel):
    id: str
    name: str
    kb_size: int
    business_id: str
    source_type: KnowledgeBaseType
    source_reference: str
    status: KnowledgeBaseStatus
    

class KnowledgeBaseResponse(KnowlegeBase):
    uploaded_at: datetime.datetime
    meta: dict
    
class TextKnowledgeBaseCreate(BaseModel):
    content: str
    label: str
    
class URLKnowledgeBaseCreate(BaseModel):
    url: str
    label: str