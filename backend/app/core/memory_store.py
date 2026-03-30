"""
MemoryStore — thread-safe session memory manager.

Each session gets its own ConversationBufferWindowMemory(k=10).
Sessions are keyed by UUID4 session_id strings.

Thread safety: FastAPI runs on multiple threads (uvicorn workers).
A single threading.Lock guards all reads/writes to the store dict.

Lifecycle:
  - get_or_create(session_id) → called at the start of every /api/chat request
  - clear_all()               → called when a new document is ingested
                                (old context is invalid for the new document)
"""

import re
import threading
from typing import Dict

from langchain.memory import ConversationBufferWindowMemory

# UUID4 pattern: xxxxxxxx-xxxx-4xxx-[89ab]xxx-xxxxxxxxxxxx
_UUID4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# Window size is fixed at 10 turns (20 messages) — not configurable in v1
_WINDOW_SIZE = 10


class MemoryStore:
    """
    In-memory registry of per-session conversation memories.

    Usage (route handler):
        memory = memory_store.get_or_create(session_id)
        response = rag_chain.query(question, session_id, memory)
        memory.save_context({"input": question}, {"output": response.answer})
    """

    def __init__(self) -> None:
        self._store: Dict[str, ConversationBufferWindowMemory] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str) -> ConversationBufferWindowMemory:
        """
        Return the existing memory for a session, or create a fresh one.

        Thread-safe: uses a lock so two concurrent requests for the same
        new session_id don't both try to create the memory object.

        Args:
            session_id: Must be a valid UUID4 string.

        Returns:
            ConversationBufferWindowMemory(k=10) for this session.

        Raises:
            ValueError: If session_id is not a valid UUID4.
        """
        self._validate_session_id(session_id)

        with self._lock:
            if session_id not in self._store:
                self._store[session_id] = ConversationBufferWindowMemory(
                    k=_WINDOW_SIZE,
                    memory_key="chat_history",
                    return_messages=True,  # Returns Message objects (not raw strings)
                )
        return self._store[session_id]

    def get_session_count(self) -> int:
        """Return the number of active sessions currently in memory."""
        with self._lock:
            return len(self._store)

    def clear_all(self) -> None:
        """
        Wipe all session memories.

        Called immediately after a new document is ingested — the old
        conversation context no longer refers to the new document, so
        all sessions must be invalidated.
        """
        with self._lock:
            self._store.clear()

    def _validate_session_id(self, session_id: str) -> None:
        """
        Raise ValueError if session_id is not a valid UUID4 string.

        Protects against path traversal, injection via session_id, and
        accidental integer/None values from misconfigured clients.
        """
        if not isinstance(session_id, str) or not _UUID4_PATTERN.match(session_id):
            raise ValueError(
                f"Invalid session_id: {session_id!r}. "
                "Must be a UUID4 string (e.g. '550e8400-e29b-41d4-a716-446655440000')."
            )
