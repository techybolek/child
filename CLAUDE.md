# CLAUDE.md

Texas Child Care Solutions RAG Application - End-to-end RAG system for Texas childcare assistance information with LangGraph orchestration.

## Environment Setup

```bash
# Required
export QDRANT_API_URL="your-qdrant-url"
export QDRANT_API_KEY="your-qdrant-key"
export OPENAI_API_KEY="your-openai-key"
export GROQ_API_KEY="your-groq-key"

# Optional overrides
export LLM_PROVIDER="groq"        # or "openai"
export RETRIEVAL_MODE="hybrid"    # or "dense"
```

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

```bash
# Load PDFs to vector database
cd LOAD_DB && python load_pdf_qdrant.py --contextual

# Run chatbot CLI
python interactive_chat.py

# Run evaluation
python -m evaluation.run_evaluation --mode hybrid --limit 5

# Web app
cd backend && python main.py      # API on :8000
cd frontend && npm run dev        # UI on :3000
```

## Architecture Overview

### 1. Vector Database (LOAD_DB/)

**Collection:** `tro-child-hybrid-v1` (unified hybrid schema)

**Hybrid Vectors:**
- Dense: OpenAI `text-embedding-3-small` (1536-dim)
- Sparse: BM25 (vocabulary 30,000)

**Three-Tier Contextual Embeddings:**
1. Master context (static domain description)
2. Document context (per-PDF summary via GROQ)
3. Chunk context (per-chunk situational context)

**Two Extractors:**
- PyMuPDF (~1s/PDF) - standard documents
- Docling (~40s/PDF) - table-heavy PDFs (configured in `TABLE_PDFS`)

**Commands:**
```bash
python load_pdf_qdrant.py --contextual      # Full load with context
python load_pdf_qdrant.py --test            # Test mode (3 PDFs)
python load_pdf_qdrant.py --no-clear        # Append to existing
python reload_single_pdf.py <filename>      # Surgical reload
python verify_qdrant.py                     # Verify collection
```

### 2. RAG Chatbot (chatbot/)

**Architecture:** LangGraph pipeline (primary) + legacy handler pattern (available)

**Pipeline Flow:**
```
Query → Classify Intent → [information] → Retrieve → Rerank → Generate → Response
                       → [location_search] → Template Response
```

**Intent Categories:**
- `information` - Policy, eligibility, program questions → RAG pipeline
- `location_search` - Facility search → Texas HHS link template

**Retrieval Modes:**
- `hybrid` - Dense + sparse with RRF fusion (prefetch 100, k=60)
- `dense` - Semantic search only

**Adaptive Reranking:**
- LLM-based scoring (0-10 scale)
- Question-type detection (enumeration vs single-fact vs complex)
- Dynamic chunk selection (5-12 chunks based on question type)
- Quality threshold: 0.60 minimum score

### 3. Evaluation System (evaluation/)

**4 Modes:** `hybrid`, `dense`, `openai`, `kendra`

**Output Structure:** `results/<mode>/RUN_<timestamp>/`

**Commands:**
```bash
python -m evaluation.run_evaluation --mode hybrid
python -m evaluation.run_evaluation --mode hybrid --resume --resume-limit 1
python -m evaluation.run_evaluation --mode kendra --debug --limit 5
```

**Key Options:**
- `--mode` - Retrieval mode (required for parallel runs)
- `--test`, `--limit N` - Limit questions
- `--resume`, `--resume-limit N` - Resume from checkpoint
- `--debug` - Show retrieval details
- `--run-name PREFIX` - Custom run directory name
- `--no-stop-on-fail` - Continue on low scores

**Scoring:** LLM-as-a-Judge with stop-on-fail at score < 70

### 4. Web Application

- **Backend:** FastAPI at `/api/chat`, `/api/health`
- **Frontend:** Next.js 15 + React 19 + Tailwind CSS

## Key Configuration

### LOAD_DB/config.py
| Setting | Value |
|---------|-------|
| `QDRANT_COLLECTION_NAME` | `'tro-child-hybrid-v1'` |
| `EMBEDDING_MODEL` | `'text-embedding-3-small'` |
| `CHUNK_SIZE` / `OVERLAP` | 1000 / 200 chars |
| `BM25_VOCABULARY_SIZE` | 30000 |
| `GROQ_MODEL` | `'openai/gpt-oss-20b'` |

### chatbot/config.py
| Setting | Value |
|---------|-------|
| `COLLECTION_NAME` | `'tro-child-hybrid-v1'` |
| `RETRIEVAL_TOP_K` | 30 |
| `RERANK_TOP_K` | 7 |
| `LLM_MODEL` | `'openai/gpt-oss-20b'` |
| `RERANKER_MODEL` | `'openai/gpt-oss-120b'` |
| `RERANK_ADAPTIVE_MODE` | `True` |
| `RRF_K` | 60 |

### evaluation/config.py
| Setting | Value |
|---------|-------|
| `VALID_MODES` | `['hybrid', 'dense', 'openai', 'kendra']` |
| `JUDGE_MODEL` | `'openai/gpt-oss-20b'` |
| `DISABLE_CITATION_SCORING` | `True` |

## Directory Structure

```
.
├── LOAD_DB/                    # Vector DB pipeline
│   ├── config.py
│   ├── load_pdf_qdrant.py
│   ├── reload_single_pdf.py
│   ├── contextual_processor.py
│   ├── text_cleaner.py
│   ├── sparse_embedder.py
│   ├── extractors/             # PyMuPDF + Docling
│   ├── shared/                 # pdf_processor, qdrant_uploader
│   └── prompts/                # Context generation prompts
├── chatbot/                    # RAG chatbot
│   ├── config.py
│   ├── chatbot.py              # LangGraph orchestrator
│   ├── graph/                  # LangGraph nodes + edges
│   │   └── nodes/              # classify, retrieve, rerank, generate, location
│   ├── handlers/               # Legacy handlers (rag, location, kendra)
│   ├── retriever.py            # Dense-only retriever
│   ├── hybrid_retriever.py     # RRF fusion retriever
│   ├── reranker.py             # LLM judge reranker
│   ├── reranker_adaptive.py    # Adaptive chunk selection
│   └── generator.py            # Response generation
├── evaluation/                 # Evaluation framework
│   ├── config.py
│   ├── run_evaluation.py
│   ├── batch_evaluator.py
│   ├── judge.py
│   └── *_evaluator.py          # Mode-specific evaluators
├── QUESTIONS/pdfs/             # Q&A test files
├── results/                    # Evaluation results by mode
├── backend/                    # FastAPI backend
├── frontend/                   # Next.js frontend
├── SCRAPER/                    # Web scraping (legacy)
└── SPECS/                      # Design documentation
```

## Documentation

Detailed specs in `SPECS/`:
- `loading_pipeline.md` - Vector DB loading details
- `evaluation_system.md` - Evaluation framework details
- `README.md` - Full documentation index

## Important

You're a pragmatic software engineer. Your only goal is to solve the stated problem using the smallest, simplest possible solution. Avoid any form of future-proofing, abstraction, optimization, or unnecessary features. Just write what is needed to meet the requirement—nothing more. Apply YAGNI and KISS principles. The code is not in production. We are working with a prototype.
