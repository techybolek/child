import os

# Judge settings
JUDGE_PROVIDER = 'groq'
JUDGE_MODEL = 'openai/gpt-oss-20b'
JUDGE_API_KEY = os.getenv('GROQ_API_KEY')

# Parallel processing
PARALLEL_WORKERS = 5

# Timeout
TIMEOUT = 30

# Checkpoint
CHECKPOINT_INTERVAL = 50

# Paths
QA_DIR = 'QUESTIONS/pdfs'
RESULTS_DIR = 'results'

# Scoring
WEIGHTS = {
    'accuracy': 0.5,
    'completeness': 0.3,
    'citation_quality': 0.1,
    'coherence': 0.1
}

THRESHOLDS = {
    'excellent': 85,
    'good': 70,
    'needs_review': 50
}

# Stop evaluation if score falls below this threshold
STOP_ON_FAIL_THRESHOLD = 60
