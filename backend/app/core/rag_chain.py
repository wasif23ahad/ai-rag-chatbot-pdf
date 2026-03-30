"""
RAG Chain — full retrieval-augmented generation pipeline.

Pipeline (per query):
  1. Embed question → FAISS retrieval (top-k chunks)
  2. Hallucination Gate: if max(scores) < threshold → return refusal, skip LLM
  3. Build prompt: SystemMessage + HumanMessage (context + history + question)
  4. Call Grok LLM (temperature=0.0, deterministic)
  5. Validate response (grounded vs refusal)
  6. Return RAGResponse

The injection guard (Layer 1) is handled UPSTREAM in the route handler,
not here. This chain assumes the question has already been cleared.
"""

import time
from copy import copy
from dataclasses import dataclass, field
from typing import List

from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory

from app.core.embedder import Embedder
from app.core.guard import Guard, REFUSAL_STRING
from app.core.vector_store import VectorStoreManager, SearchResult
from app.core.query_expansion import QueryExpander
from app.core.contextual_compression import ContextualCompressor
from app.config import get_settings

# ---------------------------------------------------------------------------
# System prompt — NEVER modify the refusal phrase (evaluation criterion)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a precise document assistant. Your ONLY job is to answer \
questions using the CONTEXT provided below.

ABSOLUTE RULES — never break these:
1. Answer ONLY using information explicitly stated in the CONTEXT section
2. Do NOT use any knowledge from your training data
3. Do NOT infer, speculate, or extrapolate beyond the CONTEXT
4. Do NOT say "based on my knowledge" or similar phrases
5. If the information is not in the CONTEXT, respond with EXACTLY this phrase \
(copy it word for word, no changes):
   "This information is not present in the provided document."
6. Do not add any words before or after the above refusal phrase
7. You may quote directly from the CONTEXT to support your answers
8. Keep answers concise and factual"""


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------


@dataclass
class RAGResponse:
    answer: str
    sources: List[SearchResult]
    is_grounded: bool
    llm_called: bool
    max_similarity_score: float
    processing_time_ms: int


# ---------------------------------------------------------------------------
# RAG Chain
# ---------------------------------------------------------------------------


class RAGChain:
    """
    Orchestrates the full RAG pipeline for a single user question.

    Args:
        vector_store: Loaded VectorStoreManager instance.
        embedder:     Embedder singleton (optional — uses default singleton).
        guard:        Guard instance (optional — uses default instance).
    """

    def __init__(
        self,
        vector_store: VectorStoreManager,
        embedder: Embedder | None = None,
        guard: Guard | None = None,
        use_query_expansion: bool = True,
        use_compression: bool = True,
    ) -> None:
        self._vector_store = vector_store
        self._embedder = embedder or Embedder.get_instance()
        self._guard = guard or Guard()
        self._settings = get_settings()
        self._llm = self._build_llm()

        # New improvements
        self._query_expander = (
            QueryExpander(max_variants=4) if use_query_expansion else None
        )
        # Disable compression - it was removing actual content
        self._compressor = None

    def _build_llm(self):
        """
        Instantiate the LLM client using OpenAI-compatible API.
        Supports Groq, xAI, and other OpenAI-compatible providers via base_url.
        temperature=0.0 is non-negotiable for factual RAG — removes creative variance.
        """
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=self._settings.llm_model,
            api_key=self._settings.api_key,
            base_url=self._settings.base_url,
            temperature=0.0,
            max_tokens=1024,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def query(
        self,
        question: str,
        session_id: str,
        memory: ConversationBufferWindowMemory,
    ) -> RAGResponse:
        """
        Run the full RAG pipeline for one user question.

        Args:
            question:   Sanitised user question (injection-checked upstream).
            session_id: UUID4 session identifier (used for logging only here).
            memory:     Session memory object — history is read from it here;
                        the caller is responsible for saving the new turn after
                        this method returns.

        Returns:
            RAGResponse with answer, sources, grounding flag, and timing.
        """
        start_ms = time.time()

        # 1. Multi-query retrieval with expansion
        if self._query_expander:
            query_variants = self._query_expander.expand(question)
            chunks: List[SearchResult] = self._vector_store.multi_query_search(
                query_variants,
                k_per_query=self._settings.faiss_top_k,
                final_k=self._settings.faiss_top_k,
            )
        else:
            chunks = self._vector_store.search(question, k=self._settings.faiss_top_k)

        scores = [r.similarity_score for r in chunks]
        max_score = max(scores) if scores else 0.0

        # 2. Hallucination gate — skip LLM if no relevant chunk found
        should_call_llm = self._guard.check_similarity_threshold(
            scores, self._settings.similarity_threshold
        )

        if not should_call_llm:
            elapsed = int((time.time() - start_ms) * 1000)
            return RAGResponse(
                answer=REFUSAL_STRING,
                sources=[],
                is_grounded=False,
                llm_called=False,
                max_similarity_score=max_score,
                processing_time_ms=elapsed,
            )

        # 3. Contextual compression — extract relevant sentences from chunks
        # Only compress large chunks (>500 chars) to avoid losing context on small chunks
        compressed_chunks = []
        if self._compressor:
            for chunk in chunks:
                # Skip compression for small chunks to preserve full context
                if len(chunk.document.page_content) < 500:
                    compressed_chunks.append(chunk)
                    continue

                compressed = self._compressor.compress(
                    chunk.document.page_content,
                    question,
                    threshold=0.35,  # Slightly lower threshold
                )
                # Create a new document with compressed text
                from copy import copy

                new_doc = copy(chunk.document)
                # Use compressed text only if it's substantial (avoid just headers)
                if len(compressed.compressed_text) > 100:
                    new_doc.page_content = compressed.compressed_text
                else:
                    # Fall back to original if compression is too aggressive
                    new_doc.page_content = chunk.document.page_content
                compressed_chunks.append(
                    SearchResult(
                        document=new_doc,
                        similarity_score=chunk.similarity_score,
                        chunk_id=chunk.chunk_id,
                        page=chunk.page,
                    )
                )
        else:
            compressed_chunks = chunks

        # 4. Load conversation history from memory
        chat_history: List[BaseMessage] = memory.load_memory_variables({}).get(
            "chat_history", []
        )

        # 5. Build structured prompt
        messages = self._build_prompt(question, compressed_chunks, chat_history)

        # 6. Call Grok LLM
        llm_response = self._llm.invoke(messages)
        raw_answer: str = llm_response.content.strip()

        # Safety truncation (2000 chars max)
        if len(raw_answer) > 2000:
            raw_answer = raw_answer[:2000]

        # 7. Validate response grounding
        is_grounded = self._guard.validate_response(raw_answer)

        elapsed = int((time.time() - start_ms) * 1000)

        # Return compressed chunks as sources (more focused citations)
        return RAGResponse(
            answer=raw_answer,
            sources=compressed_chunks,
            is_grounded=is_grounded,
            llm_called=True,
            max_similarity_score=max_score,
            processing_time_ms=elapsed,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        question: str,
        chunks: List[SearchResult],
        chat_history: List[BaseMessage],
    ) -> List[BaseMessage]:
        """
        Assemble the final prompt sent to Grok.

        Structure:
          [SystemMessage]  — strict grounding rules
          [HumanMessage]   — CONTEXT + HISTORY + QUESTION
        """
        context_str = self._format_context(chunks)
        history_str = self._format_history(chat_history)

        human_content = (
            f"CONTEXT FROM DOCUMENT:\n{context_str}\n\n"
            f"CONVERSATION HISTORY:\n{history_str}\n\n"
            f"CURRENT QUESTION: {question}"
        )

        return [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=human_content),
        ]

    def _format_context(self, chunks: List[SearchResult]) -> str:
        """
        Render retrieved chunks for inclusion in the prompt.
        Format: '--- Chunk N (Page P, Score: S) ---\\n{text}\\n'
        """
        parts: List[str] = []
        for i, result in enumerate(chunks, start=1):
            parts.append(
                f"--- Chunk {i} (Page {result.page}, "
                f"Score: {result.similarity_score:.2f}) ---\n"
                f"{result.document.page_content}"
            )
        return "\n\n".join(parts)

    def _format_history(self, history: List[BaseMessage]) -> str:
        """
        Render LangChain message history as a readable string.
        Returns 'No previous conversation.' when history is empty.
        """
        if not history:
            return "No previous conversation."
        lines: List[str] = []
        for msg in history:
            role = "User" if msg.type == "human" else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)

    def _validate_response(self, response: str) -> bool:
        """Thin wrapper kept for symmetry — delegates to Guard."""
        return self._guard.validate_response(response)
