"""
Structured JSON logger for the RAG chatbot.

Output format: one JSON object per line (JSON Lines / NDJSON).
Writes to both stdout (for Docker/cloud log collectors) and LOG_FILE.

Privacy rules (enforced by callers, documented here):
  - NEVER log raw question text
  - NEVER log raw answer text
  - NEVER log uploaded file contents
  - Log only: lengths, scores, booleans, IDs, and timing metadata

Usage:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("chat_request_completed", extra={"extra": {
        "session_id": sid,
        "question_length": len(q),
        ...
    }})

The nested extra={"extra": {...}} pattern is intentional.
Python's logging attaches flat extra keys as record attributes.
By wrapping them under a single "extra" dict, the JSONFormatter
can unpack them cleanly without inspecting every record attribute.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JSONFormatter(logging.Formatter):
    """
    Formats every log record as a single-line JSON object.
    Extra structured fields are unpacked from record.extra (a dict).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Unpack the nested extra dict (our logging convention)
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            log_entry.update(extra)

        # Attach exception traceback if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(log_file: str, log_level: str = "INFO") -> None:
    """
    Configure the root 'rag_chatbot' logger.
    Call once at application startup (in lifespan).
    Idempotent — safe to call multiple times.

    Args:
        log_file:  Path to the log file (e.g. './logs/app.log').
        log_level: Python logging level name ('DEBUG', 'INFO', 'WARNING', ...).
    """
    logger = logging.getLogger("rag_chatbot")

    # Avoid adding duplicate handlers on hot-reload
    if logger.handlers:
        return

    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = JSONFormatter()

    # Console handler (stdout — captured by Docker / cloud logging)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler — ensure directory exists first
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent propagation to the root logger (avoids duplicate output)
    logger.propagate = False


def get_logger(name: str = "rag_chatbot") -> logging.Logger:
    """
    Return a logger under the 'rag_chatbot' hierarchy.
    setup_logging() must be called before the first log is emitted
    (done in application lifespan).
    """
    return logging.getLogger(name)
