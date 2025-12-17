import os

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Qdrant settings
# Single unified collection with hybrid schema (dense + sparse vectors)
COLLECTION_NAME = 'tro-child-hybrid-v1'
EMBEDDING_MODEL = 'text-embedding-3-small'

# Retrieval settings
RETRIEVAL_TOP_K = 30
RERANK_TOP_K = 7
MIN_SCORE_THRESHOLD = 0.3

# LLM Provider settings
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # 'groq' or 'openai'

# Generation settings
LLM_MODEL = 'openai/gpt-oss-120b' if LLM_PROVIDER == 'groq' else 'gpt-4o-mini'
TEMPERATURE = 0
SEED = 42
MAX_TOKENS = 2000

# Reformulator settings (for conversational mode query reformulation)
REFORMULATOR_PROVIDER = os.getenv('REFORMULATOR_PROVIDER', 'groq')  # 'groq' or 'openai'
REFORMULATOR_MODEL = 'openai/gpt-oss-120b' if REFORMULATOR_PROVIDER == 'groq' else 'gpt-4o-mini'

# Reranker settings
RERANKER_PROVIDER = os.getenv('RERANKER_PROVIDER', 'groq')  # 'groq' or 'openai'
RERANKER_MODEL = 'openai/gpt-oss-120b' if RERANKER_PROVIDER == 'groq' else 'gpt-4o-mini'

# Intent classification settings
INTENT_CLASSIFIER_PROVIDER = os.getenv('INTENT_CLASSIFIER_PROVIDER', 'groq')  # 'groq' or 'openai'
INTENT_CLASSIFIER_MODEL = 'openai/gpt-oss-20b' if INTENT_CLASSIFIER_PROVIDER == 'groq' else 'gpt-4o-mini'

# Adaptive reranking settings
RERANK_ADAPTIVE_MODE = True       # Enable adaptive selection by default
RERANK_MIN_SCORE = 0.60           # Minimum quality threshold (6/10)
RERANK_MIN_TOP_K = 5              # Minimum chunks to return
RERANK_MAX_TOP_K = 12             # Maximum chunks to return
RERANK_PREFERRED_TOP_K = 7        # Target count for normal questions

# Question complexity patterns for adaptive reranking
ENUMERATION_PATTERNS = [
    r'what.*initiatives',
    r'list\s+all',
    r'what\s+are\s+the.*programs',
    r'multiple',
    r'various',
    r'how\s+many',
    r'which.*support'
]

SINGLE_FACT_PATTERNS = [
    r'what\s+is\s+the.*limit',
    r'how\s+much',
    r'what\s+percentage',
    r'specific.*amount',
    r'what\s+is\s+the\s+\w+\s+(for|of)',
    r'when\s+(is|was|did)'
]

# ===== RETRIEVAL MODE SETTINGS =====
# RETRIEVAL_MODE controls which retriever is used (not which collection)
# 'hybrid' = QdrantHybridRetriever (dense + sparse with RRF fusion)
# 'dense' = QdrantRetriever (dense-only semantic search)
# Both use the same unified hybrid collection
RETRIEVAL_MODE = os.getenv('RETRIEVAL_MODE', 'dense')
FUSION_METHOD = 'rrf'  # Reciprocal Rank Fusion
RRF_K = 60  # Standard RRF parameter
HYBRID_PREFETCH_LIMIT = 100  # Number of candidates to retrieve from each vector type before fusion
BM25_VOCABULARY_SIZE = 30000  # BM25 sparse vector vocabulary size

# ===== QDRANT RETRY SETTINGS =====
QDRANT_MAX_RETRIES = 3  # Number of retry attempts for transient errors
QDRANT_RETRY_BASE_DELAY = 1.0  # Base delay in seconds (exponential backoff)

# ===== AMAZON KENDRA SETTINGS =====
KENDRA_INDEX_ID = "4aee3b7a-0217-4ce5-a0a2-b737cda375d9"
KENDRA_REGION = "us-east-1"
KENDRA_TOP_K = 7

# ===== OPENAI AGENT SETTINGS =====
OPENAI_VECTOR_STORE_ID = os.getenv('OPENAI_VECTOR_STORE_ID', 'vs_69210129c50c81919a906d0576237ff5')
OPENAI_AGENT_MODEL = os.getenv('OPENAI_AGENT_MODEL', 'gpt-5-nano')

# ===== VERTEX AI AGENT SETTINGS =====
VERTEX_PROJECT_ID = os.getenv('VERTEX_PROJECT_ID', 'docker-app-20250605')
VERTEX_LOCATION = os.getenv('VERTEX_LOCATION', 'us-west1')
VERTEX_CORPUS_NAME = os.getenv('VERTEX_CORPUS_NAME', 'projects/112470053465/locations/us-west1/ragCorpora/2305843009213693952')
VERTEX_AGENT_MODEL = os.getenv('VERTEX_AGENT_MODEL', 'gemini-2.5-flash')
VERTEX_SIMILARITY_TOP_K = 10

# ===== BEDROCK KB AGENT SETTINGS =====
BEDROCK_KB_ID = os.getenv('BEDROCK_KB_ID', '371M2G58TV')
BEDROCK_AGENT_MODEL = os.getenv('BEDROCK_MODEL', 'nova-pro')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# ===== LANGGRAPH SETTINGS =====
# When True (default): Enables conversation memory with query reformulation
# When False: Uses LangGraph with stateless behavior (no memory between turns)
CONVERSATIONAL_MODE = os.getenv("CONVERSATIONAL_MODE", "true").lower() == "true"

# Generator history injection for multi-hop reasoning
# Number of recent Q&A pairs to inject into generator prompt for entity reference resolution
GENERATOR_HISTORY_TURNS = 3
