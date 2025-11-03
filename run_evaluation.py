#!/usr/bin/env python3
"""
LLM-as-a-Judge Evaluation System for Texas Childcare Chatbot

Usage:
    python run_evaluation.py                    # Evaluate all Q&A pairs
    python run_evaluation.py --test --limit 5   # Test with 5 questions
    python run_evaluation.py --file <filename>  # Evaluate specific file
"""
import argparse
from evaluation.batch_evaluator import BatchEvaluator
from evaluation.reporter import Reporter


def main():
    parser = argparse.ArgumentParser(description='Evaluate chatbot using LLM-as-a-judge')
    parser.add_argument('--test', action='store_true', help='Test mode')
    parser.add_argument('--limit', type=int, help='Limit number of questions to evaluate')
    parser.add_argument('--file', type=str, help='Evaluate specific Q&A file')
    parser.add_argument('--collection', type=str, help='Qdrant collection name')
    args = parser.parse_args()

    print("=" * 80)
    print("CHATBOT EVALUATION SYSTEM - LLM as a Judge")
    print("=" * 80)
    if args.collection:
        print(f"\nUsing Qdrant collection: {args.collection}")
    else:
        from chatbot import config
        print(f"\nUsing Qdrant collection: {config.COLLECTION_NAME} (default)")

    # Initialize
    evaluator = BatchEvaluator(collection_name=args.collection)
    reporter = Reporter()

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
