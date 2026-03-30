from supabase import create_client, Client
from app.core.config import settings
from functools import lru_cache

@lru_cache()
def get_supabase_client() -> Client:
    """
    Create Supabase client with service role key.
    Use this for admin operations only.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY
    )

@lru_cache()
def get_supabase_publishable_client() -> Client:
    """
    Create Supabase client with anon key.
    Use this for user-facing operations.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_PUBLISHABLE_KEY
    )