from fastapi import UploadFile, HTTPException, status
from app.core.config import settings


_PDF_MAGIC_BYTES = b"%PDF"
_MAX_BYTES = settings.MAX_PDF_SIZE_MB * 1024 * 1024


class PDFValidator:

    @staticmethod
    async def validate(file: UploadFile) -> bytes:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only PDF files are accepted.",
            )

        if file.content_type not in ("application/pdf", "application/octet-stream"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Invalid content type. Must be application/pdf.",
            )

        file_bytes = await file.read()

        if len(file_bytes) > _MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_PDF_SIZE_MB}MB.",
            )

        if not file_bytes.startswith(_PDF_MAGIC_BYTES):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File content is not a valid PDF.",
            )

        return file_bytes