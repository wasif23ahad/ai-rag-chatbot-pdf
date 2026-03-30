# ==============================================================================
# Backend Dockerfile — RAG Document Chatbot
# ==============================================================================
# Single-stage build using uv for fast dependency management.
# Optimised for Render free tier (512 MB RAM, 0.1 CPU).
# ==============================================================================

FROM python:3.12-slim

# Install system deps required by pdfminer / FAISS / healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for blazing-fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# ── Dependency layer (cached unless pyproject.toml/uv.lock change) ──────────
COPY pyproject.toml uv.lock ./

# Install into a fast uv .venv
RUN uv sync --locked --no-install-project --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# ── Application code ────────────────────────────────────────────────────────
COPY app/ ./app/

# Create runtime directories
RUN mkdir -p /app/data/faiss_index /app/data/uploads /app/logs

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    HF_HOME=/app/.cache/huggingface

# Expose port (Render uses $PORT, defaults to 10000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Start uvicorn — Render injects $PORT automatically
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
