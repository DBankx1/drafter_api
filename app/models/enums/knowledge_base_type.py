from enum import Enum

class KnowledgeBaseType(Enum):
    URL = "URL"
    PDF = "PDF"
    TEXT = "TEXT"
    IMAGE = "IMAGE"

class KnowledgeBaseStatus(Enum):
    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"