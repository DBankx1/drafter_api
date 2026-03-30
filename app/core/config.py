from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )
    
    API_V1_STR: str = "/api/v1"
    
    DB_URL: str = "sqlite:///./test.db"
    
    OPENAI_API_KEY: str
    
    SUPABASE_URL: str
    SUPABASE_JWT_URL: str
    SUPABASE_PUBLISHABLE_KEY: str 
    SUPABASE_SECRET_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_AUDIENCE: str = "authenticated"
    SUPABASE_STORAGE_BUCKET: str = "knowledge-bases"
    
    PGADMIN_EMAIL: str = ""
    PGADMIN_PASSWORD: str = ""

    
    ALGORITHM: str = "ES256"
    
    EMBEDDING_MODEL: str ="text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    
    REDIS_URL: str = "redis://redis:6379/0"
    
    MAX_PDF_SIZE_MB: int = 20
        
settings = Settings() # type: ignore