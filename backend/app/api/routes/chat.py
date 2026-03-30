"""POST /api/chat — Query the ingested document with a question."""

from fastapi import APIRouter, HTTPException

from app.dependencies import guard, memory_store, rag_chain, vector_store
from app.models.request import ChatRequest
from app.models.response import ChatResponse, SourceChunk
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("rag_chatbot.chat")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    RAG chat pipeline:
      1. Validate session_id (UUID4) — memory_store raises ValueError if invalid
      2. Prompt injection guard — return 400 if detected
      3. Ensure FAISS index is loaded — return 400 if no document ingested yet
      4. Retrieve + hallucination gate + LLM (or direct refusal)
      5. Save turn to session memory
      6. Return ChatResponse with answer and source citations

    HTTP status codes:
      200  Success (answer may be the refusal string — check is_grounded)
      400  Injection detected / no document ingested / invalid session_id
      422  Request body validation error (empty question, etc.)
      500  Unexpected server error
    """
    # 1. Validate session_id format
    try:
        memory = memory_store.get_or_create(request.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 2. Prompt injection guard (Layer 1 defence)
    is_injection, pattern_name = guard.check_injection(request.question)
    if is_injection:
        logger.warning(
            "injection_detected",
            extra={
                "extra": {
                    "endpoint": "/api/chat",
                    "session_id": request.session_id,
                    "injection_detected": True,
                    "injection_pattern": pattern_name,   # INTERNAL ONLY — never surfaced in API response
                    "question_length": len(request.question),
                }
            },
        )
        # Never reveal detection logic to caller
        raise HTTPException(status_code=400, detail="Invalid input detected.")

    # 3. Ensure a document has been ingested
    if not vector_store.is_loaded():
        raise HTTPException(
            status_code=400,
            detail="No document has been ingested yet. Please upload a document first.",
        )

    # 4. Run RAG pipeline (embed → retrieve → gate → LLM → validate)
    rag_response = rag_chain.query(
        question=request.question,
        session_id=request.session_id,
        memory=memory,
    )

    # 5. Save this turn to session memory
    memory.save_context(
        {"input": request.question},
        {"output": rag_response.answer},
    )

    logger.info(
        "chat_request_completed",
        extra={
            "extra": {
                "endpoint": "/api/chat",
                "status_code": 200,
                "session_id": request.session_id,
                "question_length": len(request.question),
                "chunks_retrieved": len(rag_response.sources),
                "max_similarity_score": rag_response.max_similarity_score,
                "llm_called": rag_response.llm_called,
                "answer_length": len(rag_response.answer),
                "processing_time_ms": rag_response.processing_time_ms,
                "is_grounded": rag_response.is_grounded,
            }
        },
    )

    # 6. Build response (truncate source previews to 200 chars)
    sources = [
        SourceChunk(
            chunk_id=sr.chunk_id,
            page=sr.page,
            similarity_score=sr.similarity_score,
            text_preview=sr.document.page_content[:200],
        )
        for sr in rag_response.sources
    ]

    return ChatResponse(
        session_id=request.session_id,
        answer=rag_response.answer,
        sources=sources,
        is_grounded=rag_response.is_grounded,
        processing_time_ms=rag_response.processing_time_ms,
    )
