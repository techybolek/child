import os

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
QDRANT_API_URL = os.getenv('QDRANT_API_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Qdrant settings
COLLECTION_NAME = 'tro-child-1'
EMBEDDING_MODEL = 'text-embedding-3-small'

# Retrieval settings
RETRIEVAL_TOP_K = 20
RERANK_TOP_K = 7
MIN_SCORE_THRESHOLD = 0.3

# Generation settings
LLM_MODEL = 'gpt-4-turbo-preview'
TEMPERATURE = 0.1
MAX_TOKENS = 1000
