"""GET /api/health — Liveness and readiness check."""

from fastapi import APIRouter

from app.config import get_settings
from app.dependencies import memory_store, vector_store
from app.models.response import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Returns the current operational state of the backend:
      - Whether the FAISS index is loaded (i.e. a document has been ingested)
      - Number of chunks in the index
      - Number of active chat sessions
      - Model identifiers for observability

    Always returns HTTP 200. Check 'index_loaded' to know if the system is
    ready to answer questions.
    """
    return HealthResponse(
        status="healthy",
        index_loaded=vector_store.is_loaded(),
        chunk_count=vector_store.get_chunk_count(),
        active_sessions=memory_store.get_session_count(),
        model=settings.llm_model,
        embedding_model=settings.embedding_model.split("/")[-1],
    )
