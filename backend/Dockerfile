# ==============================================================================
# Backend Dockerfile - RAG Document Chatbot
# ==============================================================================
# Multi-stage build using uv for fast package management
# ==============================================================================

FROM python:3.11-slim AS builder

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (no virtual environment needed with --system)
RUN uv sync --system --no-install-project

# ==============================================================================
# Production stage
# ==============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies for PDF/DOCX processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code (not .env - it's mounted at runtime)
COPY app/ ./app/
COPY main.py ./

# Create data and logs directories
RUN mkdir -p /app/data/faiss_index /app/data/uploads /app/logs && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Pre-download embedding model on startup to avoid cold start delays
# The model will be cached in a Docker volume for reuse
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" || true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
