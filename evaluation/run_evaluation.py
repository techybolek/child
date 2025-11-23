#!/usr/bin/env python3
"""
LLM-as-a-Judge Evaluation System for Texas Childcare Chatbot

Usage:
    python -m evaluation.run_evaluation --mode hybrid           # Evaluate using hybrid retrieval
    python -m evaluation.run_evaluation --mode dense            # Evaluate using dense-only retrieval
    python -m evaluation.run_evaluation --mode openai           # Evaluate OpenAI agent
    python -m evaluation.run_evaluation --test --limit 5        # Test with 5 questions
    python -m evaluation.run_evaluation --file <filename>       # Evaluate specific file
    python -m evaluation.run_evaluation --resume --mode hybrid  # Resume from mode-specific checkpoint
    python -m evaluation.run_evaluation --clear-checkpoint      # Delete checkpoint after successful completion

Parallel Mode Example (run in separate terminals):
    python -m evaluation.run_evaluation --mode hybrid
    python -m evaluation.run_evaluation --mode dense
    python -m evaluation.run_evaluation --mode openai
"""
import argparse
import sys
from pathlib import Path

# Support both module execution and direct script execution
try:
    from .batch_evaluator import BatchEvaluator
    from .reporter import Reporter
    from . import config as eval_config
except ImportError:
    # Add parent directory to path for direct execution
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from evaluation.batch_evaluator import BatchEvaluator
    from evaluation.reporter import Reporter
    from evaluation import config as eval_config


def main():
    parser = argparse.ArgumentParser(description='Evaluate chatbot using LLM-as-a-judge')
    parser.add_argument('--test', action='store_true', help='Test mode')
    parser.add_argument('--limit', type=int, help='Limit number of questions to evaluate')
    parser.add_argument('--file', type=str, help='Evaluate specific Q&A file')
    parser.add_argument('--collection', type=str, help='Qdrant collection name')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--resume-limit', type=int, help='After resuming, process only first N remaining questions')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode (show retrieval and reranking details)')
    parser.add_argument('--investigate', action='store_true', help='Investigation mode: re-evaluate same question repeatedly (implies --resume --resume-limit 1 --debug, never updates checkpoint)')
    parser.add_argument('--retrieval-top-k', type=int, help='Override number of chunks to retrieve (default: from config)')
    parser.add_argument('--clear-checkpoint', action='store_true', help='Delete checkpoint after successful completion (default: keep)')
    parser.add_argument('--capture-on-error', action='store_true', help='Save failed questions to checkpoint with "failed" status (allows --resume to skip them)')
    parser.add_argument('--no-stop-on-fail', action='store_true', help='Continue evaluation even when a question scores below threshold')
    parser.add_argument('--mode', type=str, choices=eval_config.VALID_MODES, help='Evaluation mode: hybrid, dense, or openai (default: from chatbot config)')
    args = parser.parse_args()

    # Handle investigate mode - automatically set resume, resume_limit, and debug
    if args.investigate:
        args.resume = True
        args.resume_limit = 1
        args.debug = True

    print("=" * 80)
    print("CHATBOT EVALUATION SYSTEM - LLM as a Judge")
    print("=" * 80)

    # Determine mode - use arg, env var, or default to chatbot config
    from chatbot import config as chatbot_config
    mode = args.mode or chatbot_config.RETRIEVAL_MODE
    print(f"\nEvaluation Mode: {mode}")

    # Determine which evaluator to use based on mode
    custom_evaluator = None
    if mode == 'openai':
        try:
            from .openai_evaluator import OpenAIAgentEvaluator
        except ImportError:
            from evaluation.openai_evaluator import OpenAIAgentEvaluator
        custom_evaluator = OpenAIAgentEvaluator()
        print("Evaluator: OpenAI Agent (gpt-5 + FileSearch)")
    else:
        # hybrid or dense mode - use ChatbotEvaluator with retrieval_mode
        try:
            from .evaluator import ChatbotEvaluator
        except ImportError:
            from evaluation.evaluator import ChatbotEvaluator
        custom_evaluator = ChatbotEvaluator(
            collection_name=args.collection,
            retrieval_top_k=args.retrieval_top_k,
            retrieval_mode=mode
        )
        retriever_type = "Hybrid (dense + sparse)" if mode == 'hybrid' else "Dense-only"
        print(f"Evaluator: RAG Chatbot ({retriever_type})")
        if args.collection:
            print(f"Collection: {args.collection}")
        else:
            print(f"Collection: {chatbot_config.COLLECTION_NAME} (default)")

    # Initialize with mode-specific output directories
    evaluator = BatchEvaluator(
        collection_name=args.collection,
        resume=args.resume,
        resume_limit=args.resume_limit,
        debug=args.debug,
        investigate_mode=args.investigate,
        retrieval_top_k=args.retrieval_top_k,
        clear_checkpoint=args.clear_checkpoint,
        capture_on_error=args.capture_on_error,
        stop_on_fail=not args.no_stop_on_fail,
        evaluator=custom_evaluator,
        mode=mode
    )
    reporter = Reporter(mode=mode)
    print(f"Results Directory: {eval_config.get_results_dir(mode)}")

    # Run evaluation
    if args.file:
        print(f"\nMode: Single file evaluation ({args.file})")
        evaluation_data = evaluator.evaluate_file(args.file)
    else:
        if args.test:
            print(f"\nMode: Test mode (limit: {args.limit or 'default'})")
        else:
            print("\nMode: Full evaluation")
        evaluation_data = evaluator.evaluate_all(limit=args.limit)

    # Generate reports
    print("\n" + "=" * 80)
    print("GENERATING REPORTS")
    print("=" * 80)
    summary = reporter.generate_reports(evaluation_data)

    # Print summary
    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Total Evaluated: {summary['total_evaluated']}")
    print(f"Composite Score: {summary['average_scores']['composite']:.1f}/100")
    print(f"Pass Rate: {summary['performance']['pass_rate']:.1f}%")
    print(f"Average Response Time: {summary['response_time']['average']:.2f}s")
    print("=" * 80)


if __name__ == '__main__':
    main()
