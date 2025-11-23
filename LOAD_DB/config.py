"""
Configuration settings for PDF to Qdrant Vector Database loader
"""

import os

# ===== PROJECT PATHS =====
# LOAD_DB directories - use direct path calculation
LOAD_DB_LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
LOAD_DB_CHECKPOINTS_DIR = os.path.join(os.path.dirname(__file__), 'checkpoints')
LOAD_DB_REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')

# Source PDF directory (where scraper outputs PDFs)
PDFS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # Project root
    'scraped_content', 'raw', 'pdfs'
)

# ===== QDRANT SETTINGS =====
# Single unified collection with hybrid schema (dense + sparse vectors)
# Dense-only or hybrid retrieval is a query-time decision, not schema decision
QDRANT_COLLECTION_NAME = 'tro-child-hybrid-v1'
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# ===== EMBEDDING SETTINGS =====
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
EMBEDDING_MODEL = 'text-embedding-3-small'  # OpenAI embedding model
EMBEDDING_DIMENSION = 1536                   # Dimension for text-embedding-3-small

# ===== TEXT CHUNKING SETTINGS =====
# Character-based chunking for vector embeddings
CHUNK_SIZE = 1000              # Characters per chunk
CHUNK_OVERLAP = 200            # Overlap between chunks
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]  # Priority order for splitting

# ===== BATCH PROCESSING =====
UPLOAD_BATCH_SIZE = 100        # Vectors to upload per batch

# ===== TABLE EXTRACTION SETTINGS =====
# PDFs that contain tables and should be processed with Docling
# Docling provides better table extraction (markdown format) but is slower (~40s per PDF)
# PDFs not in this list will use PyMuPDF (fast, ~1s per PDF)
TABLE_PDFS = [
    'bcy-26-income-eligibility-and-maximum-psoc-twc.pdf',
    'bcy-26-psoc-chart-twc.pdf',
    'evaluation-of-the-effectiveness-of-child-care-report-to-89th-legislature-twc.pdf'
]

# ===== CONTEXTUAL RETRIEVAL SETTINGS =====
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = 'openai/gpt-oss-20b'  # Same model as chatbot RAG
CONTEXT_BATCH_SIZE = 10        # Chunks per context generation batch
CONTEXT_RATE_LIMIT_DELAY = 2   # Seconds between batches
ENABLE_CONTEXTUAL_RETRIEVAL = True  # Affects dense embedding quality (context enrichment)
USE_PREVIOUS_CHUNK_CONTEXT = True  # Include previous chunk's context and text when generating chunk context

# ===== SPARSE VECTOR SETTINGS =====
# Sparse vectors always generated for hybrid schema
BM25_VOCABULARY_SIZE = 30000
