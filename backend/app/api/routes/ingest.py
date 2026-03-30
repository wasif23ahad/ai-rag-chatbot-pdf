"""POST /api/ingest — Upload and index a PDF or DOCX document."""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.dependencies import document_processor, memory_store, vector_store
from app.models.response import IngestResponse
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("rag_chatbot.ingest")

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_MB = 50


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(file: UploadFile = File(...)) -> IngestResponse:
    """
    Ingest a PDF or DOCX document:
      1. Validate file extension (422 if unsupported)
      2. Read content and enforce 50 MB size limit (413 if exceeded)
      3. Parse, chunk, embed, and build FAISS index
      4. Invalidate all existing session memories
      5. Return chunk count and confirmation

    HTTP status codes:
      200  Success
      400  Empty document (no extractable text)
      413  File exceeds 50 MB
      422  Unsupported file type or validation error
      500  Unexpected server error (caught by global handler)
    """
    # 1. Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed types: .pdf, .docx",
        )

    # 2. Read and validate file size
    content = await file.read()
    size_mb = len(content) / (1_024 * 1_024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum allowed: {MAX_FILE_SIZE_MB} MB",
        )

    # 3. Write to a temp file (processor expects a file path, not bytes)
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # 4. Parse + chunk + embed + build FAISS index
        try:
            documents = document_processor.process(tmp_path, ext)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        vector_store.build_index(documents)

        # 5. Invalidate old session memories (new doc = new context)
        memory_store.clear_all()

        logger.info(
            "ingest_completed",
            extra={
                "extra": {
                    "endpoint": "/api/ingest",
                    "status_code": 200,
                    "doc_name": file.filename,
                    "chunk_count": len(documents),
                    "file_size_mb": round(size_mb, 2),
                }
            },
        )

        return IngestResponse(
            status="success",
            doc_name=file.filename or "unknown",
            chunk_count=len(documents),
            message="Document ingested successfully. Ready to chat.",
        )

    finally:
        # Always clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
