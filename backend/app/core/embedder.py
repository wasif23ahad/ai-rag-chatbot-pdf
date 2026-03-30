"""
Embedder — Singleton wrapper around HuggingFaceEmbeddings.

The model is loaded ONCE at startup and reused for every request.
CRITICAL: the same instance must be used for both document indexing (ingest)
and query embedding (chat). Using different instances or models at each stage
causes catastrophic retrieval failure.
"""

import threading
from typing import List, Optional

from langchain_huggingface import HuggingFaceEmbeddings


class Embedder:
    """
    Thread-safe singleton embedding model.

    Usage:
        embedder = Embedder.get_instance()
        doc_vecs  = embedder.embed_texts(["chunk one", "chunk two"])
        query_vec = embedder.embed_query("what is X?")
    """

    _instance: Optional["Embedder"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, model_name: str) -> None:
        """
        Private — use get_instance() instead.
        normalize_embeddings=True maps all vectors to the unit sphere,
        so FAISS L2 distances fall in [0, 2] and convert cleanly to cosine similarity.
        """
        self.model_name = model_name
        self._embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={
                "normalize_embeddings": True,
                "batch_size": 32,
            },
        )

    @classmethod
    def get_instance(
        cls,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> "Embedder":
        """
        Return the singleton Embedder, creating it on first call.
        Double-checked locking ensures thread safety without paying
        the lock cost on every call after initialization.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_name)
        return cls._instance

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Batch-embed a list of strings. Used during document ingestion.

        Args:
            texts: List of chunk texts to embed.

        Returns:
            List of 384-dim float vectors (one per input text).
        """
        if not texts:
            return []
        return self._embeddings.embed_documents(texts)

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query string. Used at chat/query time.

        Args:
            query: The user's question.

        Returns:
            A single 384-dim float vector.
        """
        return self._embeddings.embed_query(query)

    @property
    def langchain_embeddings(self) -> HuggingFaceEmbeddings:
        """
        Expose the raw LangChain embeddings object.
        Required by FAISS.from_documents() and FAISS.load_local().
        """
        return self._embeddings
