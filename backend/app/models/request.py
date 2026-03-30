"""Pydantic request schemas for the RAG API."""

from uuid import uuid4
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="UUID4 session identifier. Auto-generated if not provided.",
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to ask about the ingested document.",
    )

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Question cannot be empty or whitespace only.")
        return v.strip()
