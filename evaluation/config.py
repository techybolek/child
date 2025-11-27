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

# Citation Scoring Toggle
DISABLE_CITATION_SCORING = True  # Set True to evaluate without citation scoring

# Valid evaluation modes
VALID_MODES = ['hybrid', 'dense', 'openai', 'kendra']

def get_results_dir(mode: str = None):
    """Get mode-specific results directory, creating if needed.

    Args:
        mode: Evaluation mode ('hybrid', 'dense', 'openai'). If None, returns base RESULTS_DIR.

    Returns:
        Path to results directory (creates if needed)
    """
    from pathlib import Path

    if mode:
        results_dir = Path(RESULTS_DIR) / mode
    else:
        results_dir = Path(RESULTS_DIR)

    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def create_run_directory(mode: str, run_name: str = None):
    """Create timestamped run directory within mode directory.

    Args:
        mode: Evaluation mode ('hybrid', 'dense', 'openai', 'kendra')
        run_name: Optional custom prefix for run directory. If not specified, defaults to 'RUN'.

    Returns:
        Path to created run directory (e.g., results/hybrid/RUN_20251125_143022/ or results/hybrid/TEST_BASIC_20251125_143022/)
    """
    from pathlib import Path
    from datetime import datetime

    mode_dir = get_results_dir(mode)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    prefix = run_name if run_name else 'RUN'
    run_dir = mode_dir / f'{prefix}_{timestamp}'

    # Handle timestamp collision (unlikely but possible)
    counter = 1
    while run_dir.exists():
        run_dir = mode_dir / f'{prefix}_{timestamp}_{counter}'
        counter += 1

    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def get_most_recent_run(mode: str):
    """Find most recent run directory for the specified mode.

    Args:
        mode: Evaluation mode ('hybrid', 'dense', 'openai', 'kendra')

    Returns:
        Path to most recent run directory, or None if no runs found
    """
    from pathlib import Path

    mode_dir = get_results_dir(mode)
    run_dirs = sorted(mode_dir.glob('RUN_*'), reverse=True)

    if run_dirs:
        return run_dirs[0]
    return None
