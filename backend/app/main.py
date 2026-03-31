"""
FastAPI application factory.

Startup (lifespan):
  - Create runtime directories (data/, logs/)
  - Attempt to load existing FAISS index from disk
    (so the server is immediately ready after a restart if a doc was ingested before)

Middleware:
  - CORS (origins from settings)
  - TimingMiddleware (adds X-Process-Time header)
  - Global exception handler (prevents 500 stack traces leaking to clients)

Routes:
  - POST /api/ingest
  - POST /api/chat
  - GET  /api/health
"""

import os
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import setup_middleware
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.config import get_settings
from app.dependencies import vector_store
from app.utils.logger import get_logger, setup_logging

settings = get_settings()
logger = get_logger("rag_chatbot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    On startup:
      - Ensure data/ and logs/ directories exist
      - Try to restore a previously built FAISS index from disk

    On shutdown:
      - No cleanup required in v1 (index is already persisted)
    """
    # Ensure runtime directories exist
    Path("data/faiss_index").mkdir(parents=True, exist_ok=True)
    Path("data/uploads").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Configure structured JSON logging (must happen before any log calls)
    setup_logging(log_file=settings.log_file, log_level=settings.log_level)

    # Restore FAISS index if available
    loaded = vector_store.load_index()
    if loaded:
        logger.info(
            "faiss_index_loaded_on_startup",
            extra={"extra": {"chunk_count": vector_store.get_chunk_count()}},
        )
    else:
        logger.info("faiss_index_not_found__waiting_for_first_ingestion")

    yield

    # Shutdown — nothing to clean up in v1


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Document Chatbot",
        description="Upload a PDF/DOCX and chat with its contents. Powered by xAI Grok + FAISS.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — allow configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Timing header + global 500 handler
    setup_middleware(app)

    # API routes
    app.include_router(ingest_router, prefix="/api", tags=["Ingest"])
    app.include_router(chat_router, prefix="/api", tags=["Chat"])
    app.include_router(health_router, prefix="/api", tags=["Health"])

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
