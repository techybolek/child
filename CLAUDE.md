# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Texas Child Care Solutions RAG Application - A complete end-to-end retrieval-augmented generation (RAG) system for Texas childcare assistance information. The system scrapes content from multiple sources, loads it into a Qdrant vector database, and provides an interactive conversational chatbot.

## System Architecture

The project consists of four main components:

### 1. Web Scraping Pipeline (SCRAPER/)
Extracts content from Texas childcare websites in multiple formats (HTML, .docx, .xlsx, PDFs).

**Key modules:**
- `config.py` - Central configuration (domains, URL patterns, chunking settings)
- `scraper.py` - Multi-format scraping engine using Playwright and BeautifulSoup
- `document_extractor.py` - Extracts content from .docx and .xlsx files
- `pdf_extractor.py` - PDF text extraction
- `content_processor.py` - Text cleaning, chunking, and deduplication
- `site_mapper.py` - Site structure analysis
- `run_pipeline.py` - Orchestrates the 3-phase scraping process

### 2. Vector Database Pipeline (LOAD_DB/)
Loads PDF documents into Qdrant vector database with OpenAI embeddings.

**Key modules:**
- `config.py` - Vector DB configuration (Qdrant, embeddings, chunking)
- `load_pdf_qdrant.py` - Main loading script using LangChain
- `verify_qdrant.py` - Collection verification and testing

### 3. RAG Chatbot (chatbot/)
Multi-provider conversational AI with **intent-based routing** and handler pattern architecture.

**Architecture:**
- **Intent Classification Layer** - Routes queries to appropriate handlers
- **RAG Pipeline** (for information queries) - Retrieval → Reranking → Generation
- **Template Responses** (for location searches) - Direct user to Texas HHS facility search

**Key modules:**
- `config.py` - Chatbot-specific configuration (LLM providers, models, intent classifier)
- `intent_router.py` - Query classification and routing logic
- `handlers/base.py` - BaseHandler interface
- `handlers/rag_handler.py` - Information queries via RAG pipeline
- `handlers/location_handler.py` - Location search template responses
- `retriever.py` - Qdrant vector search (dense-only)
- `hybrid_retriever.py` - Hybrid search with RRF fusion (dense + sparse vectors)
- `reranker.py` - LLM-based relevance scoring
- `generator.py` - Answer generation with citations
- `chatbot.py` - Main orchestration (delegates to IntentRouter)
- `interactive_chat.py` (root) - CLI interface

### 4. Web Frontend (backend/ + frontend/)
**Decoupled web architecture:** FastAPI backend wrapping the chatbot + Next.js 15 frontend with React 19.

**Backend (backend/):**
- FastAPI REST API exposing chatbot functionality
- Singleton pattern wrapping `TexasChildcareChatbot`
- Auto-generated Swagger docs at `/docs`
- Endpoints: `POST /api/chat`, `GET /api/health`

**Frontend (frontend/):**
- Next.js 15 with App Router and Turbopack
- TypeScript + React 19 + Tailwind CSS
- 7 React components: ChatInterface, MessageList, MessageBubble, InputBar, SourceCard, LoadingIndicator, ErrorMessage
- Real-time API calls with loading states
- Markdown rendering for formatted answers
- Collapsible source citations

## Environment Setup

### Required Environment Variables

```bash
# Qdrant (required for all pipelines)
export QDRANT_API_URL="your-qdrant-url"
export QDRANT_API_KEY="your-qdrant-key"

# OpenAI (required for embeddings and optional for chatbot)
export OPENAI_API_KEY="your-openai-key"

# GROQ (optional, but default provider for chatbot)
export GROQ_API_KEY="your-groq-key"

# Optional: Override provider defaults
export LLM_PROVIDER="groq"  # or "openai"
export RERANKER_PROVIDER="groq"  # or "openai"
```

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for scraping only)
playwright install chromium
```

## Common Commands

### Web Scraping
```bash
# Full scraping pipeline (3 phases: scrape → process → analyze)
cd SCRAPER
python run_pipeline.py

# Test mode (limited pages)
python run_pipeline.py --dry-run

# Output: scraped_content/processed/content_chunks.json
```

### Load PDFs to Vector Database
```bash
# Load all PDFs (clears collection first by default)
cd LOAD_DB
python load_pdf_qdrant.py

# Test with limited PDFs
python load_pdf_qdrant.py --test

# Append to existing collection (don't clear)
python load_pdf_qdrant.py --no-clear

# Verify collection
python verify_qdrant.py
```

### Run Chatbot (CLI)
```bash
# Interactive CLI chatbot
python interactive_chat.py

# Quick test
python test_chatbot.py
```

### Run Web Application
```bash
# Terminal 1: Backend API (port 8000)
cd backend
source ../.venv/bin/activate
pip install -r requirements.txt  # First time only
python main.py
# Or: uvicorn main:app --reload --port 8000

# Terminal 2: Frontend (port 3000)
cd frontend
npm install  # First time only
npm run dev

# Access:
# - Frontend UI: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

## Key Configuration Details

### Scraper Configuration (SCRAPER/config.py)

Scraper-specific settings:
- **Scraping settings:** Allowed domains, seed URLs, rate limiting, timeouts
- **Content filters:** Excluded PDFs, minimum content thresholds
- **Content processing:** Chunking (in words), content type classification
- **Directory paths:** Output directories for scraped content

### Vector Database Configuration (LOAD_DB/config.py)

Vector database-specific settings:
- **Qdrant settings:** Collection name, API URL/key
- **Embeddings:** OpenAI embedding model and dimensions
- **Chunking:** Two strategies based on PDF type (see Item-Level Chunking below)
- **Batch processing:** Upload batch sizes

### Item-Level Chunking for Table PDFs

**Two-Strategy Chunking System**:

**PyMuPDF PDFs** (standard documents):
- Uses `RecursiveCharacterTextSplitter` from LangChain
- Chunk size: 1000 characters with 200-char overlap (20%)
- Arbitrary character boundaries
- Overlap preserves context across splits

**Docling PDFs** (documents with tables, configured in `config.TABLE_PDFS`):
- Uses item-level chunking (semantic units)
- **No overlap** - relies on semantic boundaries
- Tables: One chunk per table (markdown format)
- Narrative: Accumulates until ~1000 chars, chunks at natural breaks
- Reading order preserved via y-position sorting
- Small chunks (<300 chars) merged with previous chunk

**Key Differences**:
| Aspect | PyMuPDF | Docling |
|--------|---------|---------|
| **Boundaries** | Character count (arbitrary) | Semantic units (natural) |
| **Overlap** | 200 chars | None |
| **Tables** | Mixed with text | Separated, markdown format |
| **Reading Order** | Sequential pages | Inline tables preserved |

**Configuration** (`LOAD_DB/config.py`):
```python
# PDFs requiring Docling extraction (tables + structure)
TABLE_PDFS = [
    'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf',
    'evaluation-effectiveness-child-care-program-84-legislature-twc.pdf',
    # ... 9 more PDFs with complex tables
]

# Standard chunking settings (for PyMuPDF)
CHUNK_SIZE = 1000       # Characters per chunk
CHUNK_OVERLAP = 200     # Overlap between chunks

# Item-level chunking (for Docling) - hardcoded in create_chunks_from_items()
NARRATIVE_THRESHOLD = 1000  # Target chars for narrative chunks
NARRATIVE_MIN = 300         # Minimum chunk size before merging
```

**Results** (tested on 17-page evaluation PDF):
- 43 chunks (9 tables, 34 narrative)
- Tables inline with narrative (reading order preserved)
- 95.3% of chunks ≥300 chars
- Average chunk size: 1133 chars

See `SPECS/item_level_chunking_results.md` for full details.

### Chatbot Configuration (chatbot/config.py)

Chatbot-specific settings:
- LLM provider selection (GROQ/OpenAI)
- Model names for generation and reranking
- Intent classifier provider and model
- Retrieval parameters (top_k, thresholds)
- Qdrant collection settings

### Important Constants

**SCRAPER/config.py:**
```python
CHUNK_MIN_WORDS = 500          # Word-based chunking
CHUNK_MAX_WORDS = 1000
CHUNK_OVERLAP_WORDS = 150
MAX_PAGES = 500                # Total pages to scrape
```

**LOAD_DB/config.py:**
```python
QDRANT_COLLECTION_NAME = 'tro-child-1'
EMBEDDING_MODEL = 'text-embedding-3-small'
EMBEDDING_DIMENSION = 1536
CHUNK_SIZE = 1000              # Character-based chunking
CHUNK_OVERLAP = 200
UPLOAD_BATCH_SIZE = 100
```

**chatbot/config.py:**
```python
LLM_PROVIDER = 'groq'          # default
LLM_MODEL = 'openai/gpt-oss-20b' if using GROQ
RERANKER_PROVIDER = 'groq'     # default
RERANKER_MODEL = 'openai/gpt-oss-20b' if using GROQ
INTENT_CLASSIFIER_PROVIDER = 'groq'  # default
INTENT_CLASSIFIER_MODEL = 'openai/gpt-oss-20b' if using GROQ
RETRIEVAL_MODE = 'hybrid'      # 'hybrid' or 'dense'
RETRIEVAL_TOP_K = 20
RERANK_TOP_K = 7
```

## Directory Structure

```
.
├── SCRAPER/                    # Web scraping pipeline
│   ├── config.py              # Central config (used by all pipelines)
│   ├── scraper.py
│   ├── document_extractor.py
│   ├── content_processor.py
│   └── run_pipeline.py
├── LOAD_DB/                   # Vector DB pipeline
│   ├── config.py             # Vector DB configuration
│   ├── load_pdf_qdrant.py    # Main loader
│   ├── verify_qdrant.py      # Verification
│   ├── logs/                 # Loading logs
│   ├── checkpoints/          # Progress checkpoints
│   └── reports/              # Loading reports
├── chatbot/                   # RAG chatbot
│   ├── config.py             # Chatbot-specific config
│   ├── chatbot.py            # Main orchestration (delegates to router)
│   ├── intent_router.py      # Query classification and routing
│   ├── handlers/             # Intent handlers
│   │   ├── __init__.py
│   │   ├── base.py           # BaseHandler interface
│   │   ├── rag_handler.py    # Information queries (RAG pipeline)
│   │   └── location_handler.py # Location search queries
│   ├── retriever.py          # Qdrant vector search
│   ├── reranker.py           # LLM-based relevance scoring
│   └── generator.py          # Answer generation
├── backend/                   # FastAPI web backend
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Backend configuration
│   ├── api/
│   │   ├── routes.py         # API endpoints
│   │   ├── models.py         # Pydantic schemas
│   │   └── middleware.py     # CORS, error handling
│   ├── services/
│   │   └── chatbot_service.py # Singleton wrapper
│   └── requirements.txt      # FastAPI dependencies
├── frontend/                  # Next.js 15 web frontend
│   ├── app/
│   │   ├── layout.tsx        # Root layout
│   │   ├── page.tsx          # Home page
│   │   └── globals.css       # Global styles
│   ├── components/
│   │   ├── ChatInterface.tsx    # Main container
│   │   ├── MessageList.tsx      # Message history
│   │   ├── MessageBubble.tsx    # Individual message
│   │   ├── InputBar.tsx         # Input field
│   │   ├── SourceCard.tsx       # Source citations
│   │   ├── LoadingIndicator.tsx # Loading state
│   │   └── ErrorMessage.tsx     # Error display
│   ├── lib/
│   │   ├── api.ts            # API client
│   │   ├── types.ts          # TypeScript types
│   │   └── utils.ts          # Utilities
│   └── package.json          # Node dependencies
├── scraped_content/           # Scraper output
│   ├── raw/                  # Raw scraped data
│   │   ├── pages/            # HTML page JSON
│   │   ├── pdfs/             # Downloaded PDFs + metadata
│   │   └── documents/        # .docx/.xlsx + metadata
│   ├── processed/            # Processed output
│   │   ├── content_chunks.json
│   │   └── site_map.json
│   └── reports/              # Analysis reports
├── SPECS/                     # Design documents
│   ├── web_frontend_design.md    # Web architecture
│   └── nextjs_15_updates.md      # Next.js 15 notes
├── interactive_chat.py        # CLI interface
├── test_chatbot.py           # Quick test script
└── requirements.txt          # Python dependencies
```

## Pipeline Dependencies

1. **Web Scraper** (SCRAPER/) → Outputs to `scraped_content/raw/pdfs/`
   - Uses `SCRAPER/config.py` for scraping settings
2. **Vector DB Loader** (LOAD_DB/) → Reads from `scraped_content/raw/pdfs/` and loads to Qdrant
   - Uses `LOAD_DB/config.py` for Qdrant and embedding settings
3. **Chatbot** (chatbot/) → Queries Qdrant collection `tro-child-1`
   - Uses `chatbot/config.py` for LLM and retrieval settings

Each pipeline has independent configuration and can run independently once its inputs are available.

## Intent-Based Routing Architecture

The chatbot uses an **intent classification layer** to route queries to specialized handlers:

### Intent Classification
- **Provider:** GROQ (default) or OpenAI
- **Model:** `llama-3.3-70b-versatile` (GROQ) or `gpt-4o-mini` (OpenAI)
- **Categories:**
  - `location_search` - User wants to find/search for childcare facilities
  - `information` - User wants information about policies, eligibility, programs

### Handlers
1. **LocationSearchHandler** - Returns template response with link to Texas HHS facility search
2. **RAGHandler** - Runs full RAG pipeline (Retrieval → Reranking → Generation)

### Response Format
All handlers return a dict with:
- `answer` (str) - The response text
- `sources` (list) - Source citations with doc, page, url
- `response_type` (str) - 'location_search' or 'information'
- `action_items` (list) - Optional actionable links/buttons

## Multi-Provider Support (Chatbot)

The chatbot supports multiple LLM providers via environment variables:

```bash
# Use GROQ (default, faster, free tier available)
export LLM_PROVIDER="groq"
export GROQ_API_KEY="your-key"

# Use OpenAI (higher quality, costs money)
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="your-key"

# Override intent classifier provider (optional)
export INTENT_CLASSIFIER_PROVIDER="openai"
```

Generator, reranker, and intent classifier can use different providers independently.

## Critical Architecture Notes

### Config File Hierarchy
- **SCRAPER/config.py**: Scraper-specific settings (domains, URLs, chunking in words)
- **LOAD_DB/config.py**: Vector DB settings (Qdrant, embeddings, chunking in characters)
- **chatbot/config.py**: Chatbot-only settings (LLM providers, retrieval params)
- Each pipeline has independent configuration; no shared configs

### LangChain Integration
The LOAD_DB pipeline evolved through 4 phases:
1. Manual PyMuPDF extraction
2. **LangChain refactoring** (current) - Uses `PyMuPDFLoader` for automatic document loading
3. Collection management
4. OpenAI embeddings migration

Always use LangChain's document loaders and text splitters for consistency.

### Checkpoint System
The PDF loader saves checkpoints every 5 PDFs to `LOAD_DB/checkpoints/`. If loading fails mid-process, you must manually resume - there's no automatic resume feature yet.

### Collection Management
By default, `load_pdf_qdrant.py` **clears the collection** before loading. Use `--no-clear` to append to existing data.

## Testing Approach

```bash
# Test scraper with limited pages
cd SCRAPER
python run_pipeline.py --dry-run

# Test vector DB with 3 PDFs
cd LOAD_DB
python load_pdf_qdrant.py --test

# Test chatbot quickly
python test_chatbot.py
```

## Evaluation System

### Parallel Evaluation Modes

The evaluation system supports three retrieval modes that can run simultaneously without conflicts:

```bash
# Run in separate terminals for parallel evaluation
python -m evaluation.run_evaluation --mode hybrid   # Dense + sparse RRF fusion
python -m evaluation.run_evaluation --mode dense    # Dense-only semantic search
python -m evaluation.run_evaluation --mode openai   # OpenAI agent (gpt-5 + FileSearch)
```

### Mode-Specific Output Directories

Each mode writes to isolated subdirectories:
```
results/
├── hybrid/
│   ├── checkpoint.json
│   ├── debug_eval.txt
│   ├── detailed_results_*.jsonl
│   ├── evaluation_summary_*.json
│   └── evaluation_report_*.txt
├── dense/
│   └── ... (same structure)
└── openai/
    └── ... (same structure)
```

### Common Evaluation Commands

```bash
# Single mode evaluation
python -m evaluation.run_evaluation --mode hybrid --limit 5

# Resume from mode-specific checkpoint
python -m evaluation.run_evaluation --mode hybrid --resume

# Resume and test just the failed question
python -m evaluation.run_evaluation --mode hybrid --resume --resume-limit 1

# Debug mode with retrieval details
python -m evaluation.run_evaluation --mode dense --debug --limit 1
```

### Default Mode

When `--mode` is not specified, defaults to `chatbot.config.RETRIEVAL_MODE` (currently `hybrid`).
Override via environment variable: `export RETRIEVAL_MODE=dense`

## Known Issues

### PDF Extraction in Scraper
PyMuPDF document lifecycle bug in the web scraper prevents PDF content extraction. **Impact: Low** - Most content is available in HTML/DOCX, and the separate LOAD_DB pipeline handles PDFs correctly.

### Empty Domain Field
Documents may have empty `domain` field in metadata. `source_url` is always populated, so use that for source tracking.

## Documentation

All detailed implementation documentation is in `SPECS/`:
- `SPECS/implementation_report.md` - Web scraping details
- `SPECS/load_pdf_qdrant_implementation.md` - Vector DB details
- `SPECS/chatbot_implementation.md` - RAG chatbot details
- `SPECS/README.md` - Master index

## Output Files

After running pipelines, check these key files:
- `scraped_content/processed/content_chunks.json` - Scraped content chunks
- `LOAD_DB/reports/load_report_*.txt` - Vector DB loading results
- `LOAD_DB/logs/pdf_load_*.log` - Detailed loading logs
- `scraped_content/reports/content_analysis.txt` - Scraping analysis

## Quick Reference: Adding New Content

To add new PDFs to the vector database:
1. Place PDF files in `scraped_content/raw/pdfs/`
2. Run `cd LOAD_DB && python load_pdf_qdrant.py --no-clear` (appends to existing collection)
3. Verify with `python verify_qdrant.py`
4. Chatbot automatically uses updated collection

To change embedding model or chunk size:
1. Edit `LOAD_DB/config.py` (Vector DB configuration)
2. Re-run `load_pdf_qdrant.py` (will clear and rebuild collection)
3. No chatbot changes needed

To change scraper behavior:
1. Edit `SCRAPER/config.py` (Scraper-specific configuration)
2. Re-run `cd SCRAPER && python run_pipeline.py`

## Git Notes

This repository tracks:
- Python source code
- Configuration files
- Documentation (SPECS/)
- requirements.txt

Git ignores:
- `.venv/` - Virtual environment
- `scraped_content/` - Generated scraper output
- `LOAD_DB/logs/`, `LOAD_DB/checkpoints/`, `LOAD_DB/reports/` - Generated artifacts
- `__pycache__/` - Python cache

## Important
# You’re a pragmatic software engineer. Your only goal is to solve the stated problem using the smallest, simplest possible solution. Avoid any form of future-proofing, abstraction, optimization, or unnecessary features. Just write what is needed to meet the requirement—nothing more. Apply YAGNI and KISS principles. If the task is to write code, provide the minimal (but correct) code that works, without extra comments or explanations unless explicitly requested.
# The code is not in production. We are working with a prototype.