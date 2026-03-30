"""
Application configuration via pydantic-settings.
Reads from backend/.env (never committed).
All values have safe defaults except API_KEY (required for LLM).
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to this file's directory
_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM API Configuration (supports Groq, xAI, etc.)
    # Groq: api_key is your Groq API key, base_url is auto-configured
    # xAI: set base_url to "https://api.x.ai/v1"
    api_key: str
    base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "llama-3.3-70b-versatile"

    # Embeddings (local — no API cost)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # FAISS
    faiss_index_path: str = "./data/faiss_index"
    faiss_top_k: int = 4
    similarity_threshold: float = 0.4

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 100

    # Session memory
    max_memory_turns: int = 10

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    # CORS
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:80"]


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance — reads .env exactly once."""
    return Settings()
