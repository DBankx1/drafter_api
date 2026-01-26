from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )
    
    API_V1_STR: str = "/api/v1"
    
    DB_URL: str
    
    OPENAI_API_KEY: str
    
    SUPABASE_URL: str
    SUPABASE_JWT_URL: str
    SUPABASE_PUBLISHABLE_KEY: str 
    SUPABASE_SECRET_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_AUDIENCE: str = "authenticated"
    
    ALGORITHM: str = "ES256"
        
settings = Settings() # type: ignore