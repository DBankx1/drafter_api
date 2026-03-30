from enum import Enum

class KnowledgeBaseType(Enum):
    URL = "url"
    PDF = "pdf"
    TEXT = "text"
    IMAGE = "image"
    
class KnowledgeBaseStatus(Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    ERROR = "error"