"""
Application configuration via pydantic-settings.
Reads from backend/.env (never committed).
All values have safe defaults except XAI_API_KEY (required).
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # xAI Grok LLM
    xai_api_key: str
    grok_model: str = "grok-3"

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
