import os

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Qdrant settings
#COLLECTION_NAME = 'tro-child-1'
COLLECTION_NAME = 'tro-child-3-contextual'  # Enhanced with improved family size identification prompt
EMBEDDING_MODEL = 'text-embedding-3-small'

# Retrieval settings
RETRIEVAL_TOP_K = 30
RERANK_TOP_K = 7
MIN_SCORE_THRESHOLD = 0.3

# LLM Provider settings
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # 'groq' or 'openai'

# Generation settings
LLM_MODEL = 'openai/gpt-oss-20b' if LLM_PROVIDER == 'groq' else 'gpt-4o-mini'
TEMPERATURE = 0
SEED = 42
MAX_TOKENS = 2000

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
