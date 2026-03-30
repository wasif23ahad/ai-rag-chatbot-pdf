"""
VectorStoreManager — FAISS index lifecycle: build, persist, load, search.

Similarity score formula (documented):
    similarity = 1.0 - (l2_distance / 2.0)

When normalize_embeddings=True, all embedding vectors are unit-length.
For unit vectors, FAISS L2 distance relates to cosine similarity as:
    l2² = 2 * (1 - cosine_sim)  →  cosine_sim = 1 - (l2² / 2)
Because l2 distances from FAISS are not squared, the correct linear
approximation used here is:
    similarity ≈ 1.0 - (l2_distance / 2.0)
This maps L2 ∈ [0, 2] → similarity ∈ [0, 1] (higher = more similar).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from langchain.schema import Document
from langchain_community.vectorstores import FAISS

from app.core.embedder import Embedder


@dataclass
class SearchResult:
    """A single retrieved chunk with its similarity score."""

    document: Document
    similarity_score: float   # [0, 1] — higher is more similar
    chunk_id: str
    page: int


class VectorStoreManager:
    """
    Manages the lifecycle of the FAISS vector index.

    - build_index: embed documents and create a new index (overwrites existing)
    - load_index:  restore index from disk on server startup
    - search:      embed a query and return top-k SearchResults
    """

    def __init__(self, index_path: str, embedder: Optional[Embedder] = None) -> None:
        self._index_path = Path(index_path)
        self._embedder = embedder or Embedder.get_instance()
        self._store: Optional[FAISS] = None
        self._chunk_count: int = 0

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build_index(self, documents: List[Document]) -> None:
        """
        Embed all documents and build a new FAISS IndexFlatL2.
        Persists the index to disk immediately after building.

        Args:
            documents: List of LangChain Document objects (from DocumentProcessor).

        Raises:
            ValueError: If documents list is empty.
        """
        if not documents:
            raise ValueError("Cannot build index from an empty document list.")

        self._store = FAISS.from_documents(
            documents,
            self._embedder.langchain_embeddings,
        )
        self._chunk_count = len(documents)
        self._persist()

    def _persist(self) -> None:
        """Save index to disk as index.faiss + index.pkl."""
        if self._store is None:
            raise RuntimeError("No index in memory to persist.")
        self._index_path.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(self._index_path))

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_index(self) -> bool:
        """
        Load a previously persisted FAISS index from disk.

        Returns:
            True if index was loaded successfully, False if no index exists.

        Raises:
            RuntimeError: If the index files exist but cannot be deserialized.
        """
        faiss_file = self._index_path / "index.faiss"
        if not faiss_file.exists():
            return False

        try:
            self._store = FAISS.load_local(
                str(self._index_path),
                self._embedder.langchain_embeddings,
                allow_dangerous_deserialization=True,  # Required for LangChain FAISS pickle
            )
            self._chunk_count = self._store.index.ntotal
            return True
        except Exception as exc:
            raise RuntimeError(f"Failed to load FAISS index from disk: {exc}") from exc

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, k: int = 4) -> List[SearchResult]:
        """
        Embed the query and retrieve the top-k most similar chunks.

        Similarity score formula:
            similarity = 1.0 - (l2_distance / 2.0)
        See module docstring for derivation.

        Args:
            query: The user's question string.
            k:     Number of results to return.

        Returns:
            List[SearchResult] sorted by similarity descending.

        Raises:
            RuntimeError: If the index has not been loaded or built.
        """
        if self._store is None:
            raise RuntimeError(
                "FAISS index is not loaded. "
                "Call build_index() or load_index() first."
            )

        raw: List[tuple[Document, float]] = (
            self._store.similarity_search_with_score(query, k=k)
        )

        results: List[SearchResult] = []
        for doc, l2_distance in raw:
            # Convert L2 distance → cosine similarity ∈ [0, 1]
            similarity = max(0.0, 1.0 - (l2_distance / 2.0))
            results.append(
                SearchResult(
                    document=doc,
                    similarity_score=round(similarity, 4),
                    chunk_id=doc.metadata.get("chunk_id", "unknown"),
                    page=doc.metadata.get("page", 0),
                )
            )

        results.sort(key=lambda r: r.similarity_score, reverse=True)
        return results

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_loaded(self) -> bool:
        """Return True if an index is currently in memory."""
        return self._store is not None

    def get_chunk_count(self) -> int:
        """Return the number of chunks stored in the index."""
        return self._chunk_count
