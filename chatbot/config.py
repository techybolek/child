import os

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Qdrant settings
COLLECTION_NAME = 'tro-child-1'
EMBEDDING_MODEL = 'text-embedding-3-small'

# Retrieval settings
RETRIEVAL_TOP_K = 20
RERANK_TOP_K = 7
MIN_SCORE_THRESHOLD = 0.3

# LLM Provider settings
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # 'groq' or 'openai'

# Generation settings
LLM_MODEL = 'openai/gpt-oss-20b' if LLM_PROVIDER == 'groq' else 'gpt-5-imini'
TEMPERATURE = 0.1
MAX_TOKENS = 1000

# Reranker settings
RERANKER_PROVIDER = os.getenv('RERANKER_PROVIDER', 'groq')  # 'groq' or 'openai'
RERANKER_MODEL = 'openai/gpt-oss-20b' if RERANKER_PROVIDER == 'groq' else 'gpt-4o-mini'

# Intent classification settings
INTENT_CLASSIFIER_PROVIDER = os.getenv('INTENT_CLASSIFIER_PROVIDER', 'groq')  # 'groq' or 'openai'
INTENT_CLASSIFIER_MODEL = 'llama-3.3-70b-versatile' if INTENT_CLASSIFIER_PROVIDER == 'groq' else 'gpt-4o-mini'
