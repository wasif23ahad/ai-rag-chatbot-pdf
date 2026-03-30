"""Pydantic response schemas for the RAG API."""

from typing import List
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    status: str
    doc_name: str
    chunk_count: int
    message: str


class SourceChunk(BaseModel):
    chunk_id: str
    page: int
    similarity_score: float
    text_preview: str = Field(description="First 200 characters of the chunk text.")


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: List[SourceChunk]
    is_grounded: bool
    processing_time_ms: int


class HealthResponse(BaseModel):
    status: str
    index_loaded: bool
    chunk_count: int
    active_sessions: int
    model: str
    embedding_model: str


class ErrorResponse(BaseModel):
    error: str
