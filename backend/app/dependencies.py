"""
Singleton instances shared across all route handlers.

All objects are created once at module import time.
Routes import directly from here — never instantiate their own copies.

Initialization order matters:
  1. settings  (reads .env)
  2. embedder  (loads HuggingFace model — only once)
  3. vector_store (FAISS wrapper — index loaded in lifespan)
  4. document_processor
  5. memory_store
  6. guard
  7. rag_chain (depends on vector_store)
"""

from app.config import get_settings
from app.core.document_processor import DocumentProcessor
from app.core.embedder import Embedder
from app.core.guard import Guard
from app.core.memory_store import MemoryStore
from app.core.rag_chain import RAGChain
from app.core.vector_store import VectorStoreManager

settings = get_settings()

embedder = Embedder.get_instance(settings.embedding_model)
vector_store = VectorStoreManager(settings.faiss_index_path, embedder)
document_processor = DocumentProcessor(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
)
memory_store = MemoryStore()
guard = Guard()
rag_chain = RAGChain(
    vector_store=vector_store,
    embedder=embedder,
    guard=guard,
)
