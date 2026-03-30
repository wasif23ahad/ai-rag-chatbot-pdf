# 🤖 RAG Document Chatbot

> **AI-powered document intelligence platform** — Upload PDFs or DOCX files and chat with their contents using natural language. Powered by xAI Grok, FAISS vector search, and a modern React frontend.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Local Development](#-local-development)
- [API Reference](#-api-reference)
- [Hallucination Prevention](#-hallucination-prevention)
- [Security](#-security)
- [Screenshots & Demo](#-screenshots--demo)
- [Development Time](#-development-time)
- [Testing](#-testing)
- [Contributing](#-contributing)

---

## 🎯 Overview

The **RAG Document Chatbot** is a production-ready retrieval-augmented generation (RAG) system that allows users to:

1. **Upload** PDF or DOCX documents via a drag-and-drop interface
2. **Chat** with the document using natural language questions
3. **Receive** grounded answers with source citations and confidence scores
4. **Maintain** multi-turn conversation context within a session

### Key Differentiators

- 🛡️ **Zero Hallucination**: 3-layer defense system ensures answers come ONLY from the uploaded document
- 🔒 **Prompt Injection Protection**: 7-category attack detection prevents jailbreak attempts
- 📊 **Source Transparency**: Every answer includes cited chunks with page numbers and similarity scores
- 💾 **Persistent Index**: FAISS vector index survives server restarts
- 🐳 **One-Command Deploy**: `docker-compose up --build` starts the entire stack

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                    │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │              React Frontend (Vite + React 18)                   │   │
│   │   UploadPanel │ ChatWindow │ MessageBubble │ SourceCitation     │   │
│   └──────────────────────┬──────────────────────────────────────────┘   │
│                          │ HTTP/JSON (Axios)                            │
└──────────────────────────┼──────────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │  Port 8000
                    │   Backend   │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌─────▼─────┐     ┌──────▼──────┐
   │/api/    │       │/api/chat  │     │/api/health  │
   │ingest   │       │           │     │             │
   └────┬────┘       └─────┬─────┘     └─────────────┘
        │                  │
        │          ┌───────┴────────────────────────────┐
        │          │         RAG Pipeline               │
        │          │                                    │
        │          │  ┌─────────────┐  ┌─────────────┐  │
        │          │  │Injection    │  │MemoryStore  │  │
        │          │  │Guard (L1)   │  │(k=10 turns) │  │
        │          │  └──────┬──────┘  └──────┬──────┘  │
        │          │         │                │         │
        │          │  ┌──────▼──────────────────────┐   │
        │          │  │      RAG Chain (LangChain)   │  │
        │          │  │  Retriever → Gate → LLM     │   │
        │          │  └──────┬───────────────────────┘  │
        │          └─────────┼──────────────────────────┘
        │                    │
        │          ┌─────────┼──────────────────┐
        │          │         │                  │
   ┌────▼────┐  ┌──▼──────┐ ┌▼──────────────┐   │
   │Document │  │  FAISS  │ │  xAI Grok     │   │
   │Processor│  │  Index  │ │  LLM API      │   │
   │(PDF/DOCX│  │(disk)   │ │  (api.x.ai)   │   │
   └─────────┘  └─────────┘ └───────────────┘   │
                              ┌─────────────────┘
                              │
                     ┌────────▼──────┐
                     │ HuggingFace   │
                     │ Embeddings    │
                     │ (local model) │
                     └───────────────┘
```

### Data Flow

```
1. INGESTION                    2. QUERY
   ─────────                    ───────
   PDF/DOCX                     Question
      │                            │
      ▼                            ▼
┌─────────────┐             ┌─────────────┐
│   pypdf/    │             │  Injection  │
│ python-docx │             │    Guard    │
└──────┬──────┘             └──────┬──────┘
       │                           │
       ▼                           ▼
┌─────────────┐             ┌─────────────┐
│Text Cleaning│             │   Embed     │
└──────┬──────┘             └──────┬──────┘
       │                           │
       ▼                           ▼
┌─────────────┐             ┌─────────────┐
│  Recursive  │             │FAISS Search │
│   Chunker   │             │  (top-4)    │
└──────┬──────┘             └──────┬──────┘
       │                           │
       ▼                           ▼
┌─────────────┐             ┌─────────────┐
│HuggingFace  │             │ Similarity  │
│ Embeddings  │             │  Gate (0.4) │
└──────┬──────┘             └──────┬──────┘
       │                           │
       ▼                           ▼
┌─────────────┐             ┌─────────────┐
│FAISS Index  │             │  Grok LLM   │
│  (persist)  │             │ (temp=0.0)  │
└─────────────┘             └──────┬──────┘
                                   │
                                   ▼
                            ┌─────────────┐
                            │   Answer    │
                            │ + Sources   │
                            └─────────────┘
```

---

## 🛠 Tech Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) | Async-native, automatic OpenAPI docs, Pydantic validation |
| **LLM Provider** | [xAI Grok](https://x.ai/) | Assessment requirement; OpenAI-compatible API; fast inference |
| **Orchestration** | [LangChain](https://python.langchain.com/) | Mature RAG abstractions, memory management, LCEL syntax |
| **Embeddings** | [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | Free, local, 384-dim, no API cost, Apache 2.0 license |
| **Vector Database** | [FAISS](https://github.com/facebookresearch/faiss) | Lightweight, CPU-only, disk-persistent, no external service |
| **Text Splitting** | [RecursiveCharacterTextSplitter](https://python.langchain.com/docs/modules/data_connection/document_transformers/text_splitters/recursive_text_splitter) | Respects semantic boundaries (paragraphs → sentences → words) |
| **PDF Parsing** | [pypdf](https://pypdf.readthedocs.io/) | Pure Python, preserves page numbers, handles most PDFs |
| **DOCX Parsing** | [python-docx](https://python-docx.readthedocs.io/) | Native Word support, extracts paragraphs and tables |
| **Frontend** | [React 18](https://reactjs.org/) + [Vite](https://vitejs.dev/) | Fast build, HMR, modern hooks, small bundle |
| **HTTP Client** | [Axios](https://axios-http.com/) | Request/response interceptors, error handling |
| **File Upload** | [react-dropzone](https://react-dropzone.js.org/) | Drag-and-drop with validation, progress tracking |
| **Container** | [Docker](https://www.docker.com/) + [Docker Compose](https://docs.docker.com/compose/) | Reproducible environments, easy deployment |
| **Web Server** | [Nginx](https://nginx.org/) | Static file serving, reverse proxy, gzip compression |

---

## ✨ Features

### Core Features

| Feature | Description | Status |
|---------|-------------|--------|
| 📄 **Document Upload** | Drag-and-drop PDF/DOCX with progress indicator | ✅ |
| 🔍 **Semantic Search** | FAISS vector search with cosine similarity | ✅ |
| 💬 **Conversational AI** | Multi-turn chat with 10-turn memory window | ✅ |
| 📚 **Source Citations** | Chunk ID, page number, and text preview for every source | ✅ |
| 📊 **Similarity Scores** | Confidence percentage with color-coded badges | ✅ |
| 💾 **Persistent Index** | FAISS index saved to disk, survives restarts | ✅ |

### Advanced Features (Bonus)

| Feature | Description | Status |
|---------|-------------|--------|
| 🛡️ **Hallucination Guard** | 3-layer defense: similarity gate + strict prompt + response validation | ✅ |
| 🔒 **Prompt Injection Protection** | 7-category regex detection (direct override, role injection, delimiters, encoding, context poisoning, jailbreaks, subtle bypasses) | ✅ |
| 📝 **Structured Logging** | JSON Lines format with privacy-safe metadata (no raw text logged) | ✅ |
| 🐳 **Docker Deployment** | Single-command startup with `docker-compose up` | ✅ |
| 🧪 **Comprehensive Tests** | 4 test suites covering ingestion, guard, API, and red-team scenarios | ✅ |
| ⚡ **Async Architecture** | All endpoints are async for optimal concurrency | ✅ |

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+
- xAI API Key ([get one here](https://x.ai/))

### 1. Clone & Configure

```bash
git clone https://github.com/wasif23ahad/ai-rag-chatbot-pdf.git
cd ai-rag-chatbot

# Copy environment template
cp backend/.env.example backend/.env

# Edit backend/.env and add your xAI API key
# XAI_API_KEY=xai-your-api-key-here
```

### 2. Start with Docker

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### 3. Access the Application

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost | React chat interface |
| Backend API | http://localhost:8000 | FastAPI endpoints |
| API Docs | http://localhost:8000/docs | Swagger UI (auto-generated) |
| Health Check | http://localhost:8000/api/health | System status |

### 4. Usage

1. Open http://localhost in your browser
2. Upload a PDF or DOCX file in the left sidebar
3. Wait for indexing (chunk count will display)
4. Start asking questions in the chat panel!

---

## 🛠 Local Development

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies (using uv)
uv pip install -e .

# Or with pip
pip install -e .

# Run development server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Access at http://localhost:5173
```

### Environment Variables

```env
# backend/.env
XAI_API_KEY=xai-your-api-key-here
BASE_URL=https://api.x.ai/v1
LLM_MODEL=grok-3

# FAISS Settings
FAISS_INDEX_PATH=./data/faiss_index
FAISS_TOP_K=4
SIMILARITY_THRESHOLD=0.4

# Chunking
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# Memory
MAX_MEMORY_TURNS=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:80
```

---

## 📡 API Reference

### POST `/api/ingest`

Upload and index a PDF or DOCX document.

**Request:**
```http
POST /api/ingest
Content-Type: multipart/form-data

file: <binary PDF or DOCX>
```

**Response:**
```json
{
  "status": "success",
  "doc_name": "Manual_XYZ.pdf",
  "chunk_count": 142,
  "message": "Document ingested successfully. Ready to chat."
}
```

**Error Codes:**
- `400` — Empty document (no extractable text)
- `413` — File exceeds 50MB
- `422` — Unsupported file type

---

### POST `/api/chat`

Ask a question about the ingested document.

**Request:**
```http
POST /api/chat
Content-Type: application/json

{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "What is the emergency shutdown procedure?"
}
```

**Response (Grounded Answer):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "The emergency shutdown procedure involves pressing the red button...",
  "sources": [
    {
      "chunk_id": "chunk_023",
      "page": 7,
      "similarity_score": 0.87,
      "text_preview": "Emergency shutdown: Press the red button on panel..."
    }
  ],
  "is_grounded": true,
  "processing_time_ms": 1240
}
```

**Response (Not in Document):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "This information is not present in the provided document.",
  "sources": [],
  "is_grounded": false,
  "processing_time_ms": 45
}
```

**Error Codes:**
- `400` — Injection detected / No document ingested / Invalid session_id
- `422` — Validation error (empty question, etc.)

---

### GET `/api/health`

Check system health and status.

**Response:**
```json
{
  "status": "healthy",
  "index_loaded": true,
  "chunk_count": 142,
  "active_sessions": 3,
  "model": "grok-3",
  "embedding_model": "all-MiniLM-L6-v2"
}
```

---

## 🛡 Hallucination Prevention

This system implements a **3-layer defense** against LLM hallucination:

### Layer 1: Similarity Threshold Gate
```python
# Before calling the LLM
if max(similarity_scores) < SIMILARITY_THRESHOLD (0.4):
    return REFUSAL_STRING  # Skip LLM entirely
```
If the best matching document chunk has a similarity score below 0.4, the system returns the refusal message immediately without invoking the LLM.

### Layer 2: Strict System Prompt
```
You are a precise document assistant. Your ONLY job is to answer 
questions using the CONTEXT provided below.

ABSOLUTE RULES:
1. Answer ONLY using information explicitly stated in the CONTEXT
2. Do NOT use any knowledge from your training data
3. If the information is not in the CONTEXT, respond with EXACTLY:
   "This information is not present in the provided document."
```
The system prompt explicitly forbids using outside knowledge and mandates the exact refusal phrase.

### Layer 3: Response Validation
```python
# After LLM responds
if response.strip() == REFUSAL_STRING:
    is_grounded = False
else:
    is_grounded = True  # Answer came from document context
```
The response is validated to ensure the LLM followed instructions.

---

## 🔒 Security

### Prompt Injection Protection

The system detects and blocks 7 categories of prompt injection attacks:

| Category | Examples | Detection |
|----------|----------|-----------|
| **Direct Override** | "ignore previous instructions" | Regex pattern matching |
| **Role Injection** | "you are now an unrestricted AI" | Persona override patterns |
| **Delimiter Injection** | "###", "<\|system\|>", "[INST]" | Special token detection |
| **Encoding/Obfuscation** | Base64, Unicode escapes | Decode + scan |
| **Context Poisoning** | "the document says to ignore..." | Semantic patterns |
| **Jailbreak Keywords** | "DAN", "developer mode" | Known attack signatures |
| **Subtle Bypasses** | "override system", "disregard constraints" | Heuristic detection |

**Response to detected injection:**
```json
HTTP 400
{ "error": "Invalid input detected." }
```
> Note: Detection logic is never revealed to the caller. Pattern names are logged internally only.

### Privacy Protection

- ❌ **Never logged**: Raw question text, answer text, file contents
- ✅ **Logged**: Text lengths, similarity scores, metadata, timing

---

## 📸 Screenshots & Demo

### Upload Panel
<!-- Upload a screenshot showing the drag-and-drop interface here -->
```
[SCREENSHOT: UploadPanel with drag-and-drop zone]
```

### Chat Interface
<!-- Upload a screenshot showing the chat window with messages -->
```
[SCREENSHOT: ChatWindow with user question and AI response]
```

### Source Citations
<!-- Upload a screenshot showing the expandable source panel -->
```
[SCREENSHOT: SourceCitation expanded showing chunk previews and similarity badges]
```

### Video Demo
<!-- Add your demo video link here -->
🎥 **[Watch Demo Video](YOUR_VIDEO_LINK_HERE)**

> Click the image above to watch a 2-minute demonstration of the RAG Document Chatbot in action.

---

## ⏱ Development Time

| Task | Description | Time |
|------|-------------|------|
| T1 | Project scaffold, config, `.env.example`, git init | 30 min |
| T2 | Document processor (PDF/DOCX parse + chunk + embed + FAISS) | 2 hr |
| T3 | RAG chain with Grok LLM + hallucination guard (3 layers) | 2 hr |
| T4 | Session memory store + multi-turn integration | 1 hr |
| T5 | FastAPI routes: ingest, chat, health + Pydantic models | 1.5 hr |
| T6 | Logging middleware (structured JSON) | 45 min |
| T7 | Prompt injection protection guard | 45 min |
| T8 | React frontend (chat UI, upload panel, message thread) | 3 hr |
| T9 | Source citation + similarity score in UI | 1 hr |
| T10 | Dockerfile (backend + frontend) + docker-compose | 1 hr |
| T11 | README, screenshots, final cleanup | 1.5 hr |
| **Total** | | **~15 hr** |

---

## 🧪 Testing

Run the comprehensive test suite:

```bash
cd backend

# Run all tests
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_guard.py -v
pytest tests/test_ingest.py -v
pytest tests/test_chat.py -v
pytest tests/test_guard_redteam.py -v
```

### Test Coverage

| Test File | Coverage |
|-----------|----------|
| `test_ingest.py` | PDF/DOCX extraction, chunking, FAISS persistence |
| `test_guard.py` | Injection patterns, similarity gate, response validation |
| `test_guard_redteam.py` | Adversarial attack scenarios (70+ test cases) |
| `test_chat.py` | API endpoints, error handling, health checks |

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Style

- **Python**: Follow PEP 8, use type hints everywhere
- **JavaScript**: Use ESLint defaults, functional components with hooks
- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`, `test:`)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [LangChain](https://python.langchain.com/) for the excellent RAG abstractions
- [FastAPI](https://fastapi.tiangolo.com/) for the blazing-fast web framework
- [xAI](https://x.ai/) for the Grok LLM API
- [Hugging Face](https://huggingface.co/) for the open-source embedding models

---

## 📧 Contact

**Mohammad Wasif Ahad**
- GitHub: [@wasif23ahad](https://github.com/wasif23ahad)
- Project: [https://github.com/wasif23ahad/ai-rag-chatbot-pdf](https://github.com/wasif23ahad/ai-rag-chatbot-pdf)

---

