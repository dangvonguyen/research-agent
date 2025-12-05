import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile

from app.core.config import settings
from app.types import Attachment, Response

logger = logging.getLogger(__name__)
router = APIRouter()

# Ensure upload directory exists
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=Response[list[Attachment]])
async def upload_files(files: list[UploadFile]) -> Any:
    """
    Upload files and return attachment metadata.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    uploaded_attachments = []

    for file in files:
        # Validate file size
        content = await file.read()
        file_size = len(content)

        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File '{file.filename}' exceeds maximum size of {settings.MAX_UPLOAD_SIZE / (1024 * 1024)}MB",
            )

        # Generate unique filename
        file_ext = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # Save file
        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)

            logger.debug(
                "Successfully uploaded file '%s' as '%s' (size: %d bytes)",
                file.filename,
                unique_filename,
                file_size,
            )

            # Create attachment metadata
            attachment = Attachment(
                name=file.filename or unique_filename,
                path=f"/api/v1/uploads/{unique_filename}",  # URL path for accessing the file
                content_type=file.content_type or "application/octet-stream",
            )

            uploaded_attachments.append(attachment)

        except Exception as e:
            logger.error("Error uploading file '%s': %s", file.filename, str(e))
            raise HTTPException(
                status_code=500, detail=f"Error uploading file: {e}"
            ) from e

    return {
        "data": uploaded_attachments,
        "metadata": {
            "uploaded_count": len(uploaded_attachments),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    }
