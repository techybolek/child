# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Texas Child Care Solutions RAG Application - A complete end-to-end retrieval-augmented generation (RAG) system for Texas childcare assistance information. The system scrapes content from multiple sources, loads it into a Qdrant vector database, and provides an interactive conversational chatbot.

## System Architecture

The project consists of three independent pipelines that work together:

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
- `load_pdf_qdrant.py` - Main loading script using LangChain
- `verify_qdrant.py` - Collection verification and testing

**Important:** This pipeline uses SCRAPER/config.py for shared configuration (paths, Qdrant settings, embedding models).

### 3. RAG Chatbot (chatbot/)
Multi-provider conversational AI with 3-stage pipeline: Retrieval → Reranking → Generation.

**Key modules:**
- `config.py` - Chatbot-specific configuration (LLM providers, models)
- `retriever.py` - Qdrant vector search
- `reranker.py` - LLM-based relevance scoring
- `generator.py` - Answer generation with citations
- `chatbot.py` - Main orchestration class
- `interactive_chat.py` (root) - CLI interface

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

### Run Chatbot
```bash
# Interactive CLI chatbot
python interactive_chat.py

# Quick test
python test_chatbot.py
```

## Key Configuration Details

### Shared Configuration (SCRAPER/config.py)

The `SCRAPER/config.py` file serves as the **central configuration** for the entire project, not just the scraper:

- **Scraping settings:** Domains, URLs, rate limiting, content filters
- **Vector DB settings:** Qdrant collection name, embedding model, chunk size
- **Directory paths:** All pipelines use paths defined here

Both the scraper and LOAD_DB pipeline import from `SCRAPER/config.py`.

### Chatbot Configuration (chatbot/config.py)

Chatbot-specific settings only:
- LLM provider selection (GROQ/OpenAI)
- Model names for generation and reranking
- Retrieval parameters (top_k, thresholds)

### Important Constants

```python
# Vector DB (from SCRAPER/config.py)
QDRANT_COLLECTION_NAME = 'tro-child-1'
EMBEDDING_MODEL = 'text-embedding-3-small'
EMBEDDING_DIMENSION = 1536
CHUNK_SIZE = 1000  # characters
CHUNK_OVERLAP = 200

# Chatbot (from chatbot/config.py)
LLM_PROVIDER = 'groq'  # default
LLM_MODEL = 'openai/gpt-oss-20b' if using GROQ
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
│   ├── load_pdf_qdrant.py    # Main loader
│   ├── verify_qdrant.py      # Verification
│   ├── logs/                 # Loading logs
│   ├── checkpoints/          # Progress checkpoints
│   └── reports/              # Loading reports
├── chatbot/                   # RAG chatbot
│   ├── config.py             # Chatbot-specific config
│   ├── chatbot.py            # Main orchestration
│   ├── retriever.py
│   ├── reranker.py
│   └── generator.py
├── scraped_content/           # Scraper output
│   ├── raw/                  # Raw scraped data
│   │   ├── pages/            # HTML page JSON
│   │   ├── pdfs/             # Downloaded PDFs + metadata
│   │   └── documents/        # .docx/.xlsx + metadata
│   ├── processed/            # Processed output
│   │   ├── content_chunks.json
│   │   └── site_map.json
│   └── reports/              # Analysis reports
├── interactive_chat.py        # CLI interface
├── test_chatbot.py           # Quick test script
└── requirements.txt          # All dependencies
```

## Pipeline Dependencies

1. **Web Scraper** → Outputs to `scraped_content/raw/pdfs/`
2. **Vector DB Loader** → Reads from `scraped_content/raw/pdfs/` and loads to Qdrant
3. **Chatbot** → Queries Qdrant collection `tro-child-1`

Each pipeline can run independently once its inputs are available.

## Multi-Provider Support (Chatbot)

The chatbot supports multiple LLM providers via environment variables:

```bash
# Use GROQ (default, faster, free tier available)
export LLM_PROVIDER="groq"
export GROQ_API_KEY="your-key"

# Use OpenAI (higher quality, costs money)
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="your-key"
```

Generator and reranker can use different providers independently.

## Critical Architecture Notes

### Config File Hierarchy
- **SCRAPER/config.py**: Shared by scraper and LOAD_DB (paths, Qdrant, embeddings)
- **chatbot/config.py**: Chatbot-only settings (LLM providers, retrieval params)
- When modifying vector DB settings, update SCRAPER/config.py, not chatbot/config.py

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

## Known Issues

### PDF Extraction in Scraper
PyMuPDF document lifecycle bug in the web scraper prevents PDF content extraction. **Impact: Low** - Most content is available in HTML/DOCX, and the separate LOAD_DB pipeline handles PDFs correctly.

### Empty Domain Field
Documents may have empty `domain` field in metadata. `source_url` is always populated, so use that for source tracking.

## Performance Notes

- **Scraping:** ~30 chunks from HTML/documents (30 pages)
- **Vector DB Loading:** 42 PDFs → 3,722 chunks in ~1:45 minutes
- **Chatbot Response Time:** 3-6 seconds average (includes retrieval, reranking, generation)
- **GROQ vs OpenAI:** GROQ is significantly faster for LLM calls but OpenAI may have higher quality

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
1. Edit `SCRAPER/config.py` (NOT chatbot/config.py)
2. Re-run `load_pdf_qdrant.py` (will clear and rebuild collection)
3. No chatbot changes needed

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
