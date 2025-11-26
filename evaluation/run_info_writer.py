"""
Generate run_info.txt file capturing evaluation configuration parameters.
"""
from datetime import datetime
from pathlib import Path


def write_run_info(results_dir: Path, mode: str):
    """Write mode-specific run configuration info to run_info.txt.

    Args:
        results_dir: Mode-specific results directory (e.g., results/hybrid/)
        mode: Evaluation mode ('hybrid', 'dense', 'openai', 'kendra')
    """
    # Import configs here to avoid circular imports
    from chatbot import config as chatbot_config
    from evaluation import config as eval_config
    from LOAD_DB import config as load_config

    run_info_path = results_dir / 'run_info.txt'
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    with open(run_info_path, 'w') as f:
        f.write("=" * 65 + "\n")
        f.write("EVALUATION RUN CONFIGURATION\n")
        f.write("=" * 65 + "\n\n")

        f.write(f"Mode: {mode}\n")
        f.write(f"Timestamp: {timestamp}\n\n")

        # Mode Description
        _write_mode_description(f, mode)

        # Retrieval Configuration (mode-specific)
        _write_retrieval_config(f, mode, chatbot_config, load_config)

        # LLM Models (mode-specific)
        _write_llm_config(f, mode, chatbot_config)

        # Evaluation Settings (shared across all modes)
        _write_evaluation_settings(f, eval_config)

        f.write("=" * 65 + "\n")


def _write_mode_description(f, mode: str):
    """Write mode description section."""
    f.write("-" * 65 + "\n")
    f.write("MODE DESCRIPTION\n")
    f.write("-" * 65 + "\n")

    descriptions = {
        'hybrid': 'Dense + sparse vectors with RRF fusion',
        'dense': 'Dense-only semantic search',
        'kendra': 'AWS Kendra enterprise search with Bedrock LLM',
        'openai': 'OpenAI GPT-5 agent with FileSearch tool'
    }

    f.write(f"{descriptions.get(mode, 'Unknown mode')}\n\n")


def _write_retrieval_config(f, mode: str, chatbot_config, load_config):
    """Write mode-specific retrieval configuration."""
    f.write("-" * 65 + "\n")
    f.write("RETRIEVAL CONFIGURATION\n")
    f.write("-" * 65 + "\n")

    if mode in ['hybrid', 'dense']:
        # Qdrant-based retrieval
        f.write(f"Qdrant Collection: {chatbot_config.COLLECTION_NAME}\n")
        f.write(f"Embedding Model: {load_config.EMBEDDING_MODEL}\n")
        f.write(f"Retrieval Top K: {chatbot_config.RETRIEVAL_TOP_K}\n")
        f.write(f"Rerank Top K: {chatbot_config.RERANK_TOP_K}\n")

        if mode == 'hybrid':
            # Hybrid-specific parameters
            f.write(f"Fusion Method: {chatbot_config.FUSION_METHOD}\n")
            f.write(f"RRF K: {chatbot_config.RRF_K}\n")
            f.write(f"Prefetch Limit: {chatbot_config.HYBRID_PREFETCH_LIMIT}\n")
            f.write(f"BM25 Vocabulary Size: {chatbot_config.BM25_VOCABULARY_SIZE}\n")

    elif mode == 'kendra':
        # AWS Kendra configuration
        f.write(f"Kendra Index ID: {chatbot_config.KENDRA_INDEX_ID}\n")
        f.write(f"Kendra Region: {chatbot_config.KENDRA_REGION}\n")
        f.write(f"Kendra Top K: {chatbot_config.KENDRA_TOP_K}\n")

    elif mode == 'openai':
        # OpenAI agent configuration
        f.write("OpenAI Agent: gpt-5 with FileSearch\n")
        f.write("(Note: External configuration)\n")

    f.write("\n")


def _write_llm_config(f, mode: str, chatbot_config):
    """Write mode-specific LLM configuration."""
    f.write("-" * 65 + "\n")
    f.write("LLM MODELS\n")
    f.write("-" * 65 + "\n")

    if mode in ['hybrid', 'dense']:
        # Standard chatbot LLM configuration
        f.write(f"Generator Provider: {chatbot_config.LLM_PROVIDER}\n")
        f.write(f"Generator Model: {chatbot_config.LLM_MODEL}\n")
        f.write(f"Reranker Provider: {chatbot_config.RERANKER_PROVIDER}\n")
        f.write(f"Reranker Model: {chatbot_config.RERANKER_MODEL}\n")
        f.write(f"Intent Classifier Provider: {chatbot_config.INTENT_CLASSIFIER_PROVIDER}\n")
        f.write(f"Intent Classifier Model: {chatbot_config.INTENT_CLASSIFIER_MODEL}\n")

    elif mode == 'kendra':
        # Uses ResponseGenerator (same as dense/hybrid)
        f.write(f"Generator Provider: {chatbot_config.LLM_PROVIDER}\n")
        f.write(f"Generator Model: {chatbot_config.LLM_MODEL}\n")

    elif mode == 'openai':
        # OpenAI agent
        f.write("Generator: OpenAI gpt-5\n")

    f.write("\n")


def _write_evaluation_settings(f, eval_config):
    """Write evaluation settings (shared across all modes)."""
    f.write("-" * 65 + "\n")
    f.write("EVALUATION SETTINGS\n")
    f.write("-" * 65 + "\n")
    f.write(f"Judge Provider: {eval_config.JUDGE_PROVIDER}\n")
    f.write(f"Judge Model: {eval_config.JUDGE_MODEL}\n")
    citations_enabled = not eval_config.DISABLE_CITATION_SCORING
    f.write(f"Citations Enabled: {citations_enabled}\n\n")
