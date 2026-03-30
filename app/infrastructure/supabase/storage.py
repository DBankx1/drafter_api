
import logging

from app.core.supabase_client import get_supabase_publishable_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseStorage:
    
    def __init__(self):
        self._client = get_supabase_publishable_client()
        self._bucket = settings.SUPABASE_STORAGE_BUCKET
    
    
    def build_path(self, business_id: str, filename: str) -> str:
        """Build a consistent path for storing files in Supabase"""
        safe_filename = filename.replace("/", "_").replace("..", "_")
        return f"{business_id}/{safe_filename}"
    
    def upload_file(self, path: str, file_content: bytes) -> str:
        """Upload a file to Supabase Storage and return the public URL"""
        try:
            logger.info(f"Uploading file to Supabase at path: {path}")
            self._client.storage.from_(self._bucket).upload(path, file_content, file_options={"content-type": "application/pdf", "upsert": "false"})
            return path
        except Exception as e:
            logger.error(f"Error uploading file to Supabase: {str(e)}")
            raise
    
    def download_file(self, path: str) -> bytes:
        try:
            return self._client.storage.from_(self._bucket).download(path)
        except Exception as e:
            logger.error(f"Error downloading file from Supabase: {str(e)}")
            raise
    
    def delete_file(self, path: str) -> None:
        try:
            self._client.storage.from_(self._bucket).remove([path])
        except Exception as e:
            logger.error(f"Error deleting file from Supabase: {str(e)}")
            raise
    
    def get_signed_url(self, path: str, expired_in: int = 3600) -> str:
        try:
            response = self._client.storage.from_(self._bucket).create_signed_url(path, expired_in)            
            return response['signedURL']
        except Exception as e:
            logger.error(f"Error getting public URL from Supabase: {str(e)}")
            raise
    