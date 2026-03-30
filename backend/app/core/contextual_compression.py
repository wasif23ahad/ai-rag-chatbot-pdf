"""
Contextual Compression — Extract only relevant sentences from retrieved chunks.

When a large chunk is retrieved but only 1-2 sentences are relevant to the query,
this module extracts those sentences to:
1. Reduce noise in the LLM context
2. Lower token usage
3. Improve answer precision
4. Provide focused citations

Uses a simple embedding-based similarity approach (no extra model needed).
"""

import re
from dataclasses import dataclass
from typing import List

from app.core.embedder import Embedder


@dataclass
class CompressedChunk:
    """A chunk compressed to its most relevant sentences."""

    original_text: str
    compressed_text: str
    relevant_sentences: List[str]
    compression_ratio: float  # 0.0 to 1.0 (lower = more compressed)


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, handling common abbreviations."""
    # Simple sentence splitting - handles basic cases
    # Look for periods followed by space and capital letter, or end of string
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sentences if s.strip()]


class ContextualCompressor:
    """
    Compresses chunks by extracting only sentences relevant to the query.

    Example:
        Chunk: "The sky is blue. The API requires authentication. Water is wet."
        Query: "API authentication"
        Result: "The API requires authentication."
    """

    def __init__(
        self, embedder: Embedder | None = None, top_k_sentences: int = 3
    ) -> None:
        self._embedder = embedder or Embedder.get_instance()
        self._top_k = top_k_sentences

    def compress(
        self, text: str, query: str, threshold: float = 0.5
    ) -> CompressedChunk:
        """
        Compress a chunk to only its most relevant sentences for the query.

        Args:
            text: Original chunk text.
            query: User query to compare against.
            threshold: Minimum similarity to include a sentence.

        Returns:
            CompressedChunk with extracted relevant sentences.
        """
        sentences = split_into_sentences(text)

        if len(sentences) <= 1:
            # Nothing to compress
            return CompressedChunk(
                original_text=text,
                compressed_text=text,
                relevant_sentences=sentences,
                compression_ratio=1.0,
            )

        # Embed query and all sentences
        query_embedding = self._embedder.embed_query(query)
        sentence_embeddings = self._embedder.embed_texts(sentences)

        # Calculate cosine similarities
        similarities = []
        for sent_emb in sentence_embeddings:
            sim = self._cosine_similarity(query_embedding, sent_emb)
            similarities.append(sim)

        # Get top-k most relevant sentences (preserve original order)
        indexed_sims = list(enumerate(similarities))
        indexed_sims.sort(key=lambda x: x[1], reverse=True)

        # Filter by threshold and take top_k
        relevant_indices = [
            idx for idx, sim in indexed_sims[: self._top_k] if sim >= threshold
        ]

        if not relevant_indices:
            # No sentences met threshold, return original
            return CompressedChunk(
                original_text=text,
                compressed_text=text,
                relevant_sentences=sentences,
                compression_ratio=1.0,
            )

        # Sort by original position to maintain flow
        relevant_indices.sort()
        relevant_sents = [sentences[i] for i in relevant_indices]

        compressed_text = " ".join(relevant_sents)
        compression_ratio = len(relevant_sents) / len(sentences)

        return CompressedChunk(
            original_text=text,
            compressed_text=compressed_text,
            relevant_sentences=relevant_sents,
            compression_ratio=compression_ratio,
        )

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)
