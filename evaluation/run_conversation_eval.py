"""
Multi-turn conversation evaluation runner.

Usage:
    python -m evaluation.run_conversation_eval --conversation ccs_eligibility_conv.yaml --debug
    python -m evaluation.run_conversation_eval --all
    python -m evaluation.run_conversation_eval --mode hybrid --all
"""

import argparse
import sys
from pathlib import Path

from chatbot.chatbot import TexasChildcareChatbot
from chatbot import config
from .conversation_evaluator import ConversationEvaluator, ConversationResult
from .multi_turn_judge import MultiTurnJudge


def print_summary(results: list[ConversationResult]):
    """Print summary of all conversation evaluations."""
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)

    passed = sum(1 for r in results if r.conversation_passed)
    total = len(results)
    print(f"Conversations: {passed}/{total} passed")

    if results:
        avg = sum(r.average_score for r in results) / len(results)
        print(f"Average Score: {avg:.1f}")

        avg_context = sum(r.context_resolution_rate for r in results) / len(results)
        print(f"Context Resolution: {avg_context:.1%}")

    print()

    # Per-conversation breakdown
    for r in results:
        status = "PASS" if r.conversation_passed else "FAIL"
        print(f"  [{status}] {r.name}: {r.average_score:.1f} avg, {r.context_resolution_rate:.1%} context")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate multi-turn conversations"
    )
    parser.add_argument(
        "--mode",
        choices=["hybrid", "dense"],
        default="hybrid",
        help="Retrieval mode"
    )
    parser.add_argument(
        "--conversation",
        help="Single conversation file to evaluate"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all conversations in QUESTIONS/conversations/"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed output including reformulated queries"
    )
    args = parser.parse_args()

    # Enable conversational mode
    config.CONVERSATIONAL_MODE = True

    # Set retrieval mode
    if hasattr(config, 'RETRIEVAL_MODE'):
        config.RETRIEVAL_MODE = args.mode

    print(f"[Conversation Eval] Mode: {args.mode}")
    print(f"[Conversation Eval] CONVERSATIONAL_MODE: {config.CONVERSATIONAL_MODE}")

    # Initialize components
    chatbot = TexasChildcareChatbot()
    judge = MultiTurnJudge()
    evaluator = ConversationEvaluator(chatbot, judge)

    # Find conversation files
    conv_dir = Path("QUESTIONS/conversations")
    if args.conversation:
        files = [conv_dir / args.conversation]
        if not files[0].exists():
            print(f"ERROR: Conversation file not found: {files[0]}")
            sys.exit(1)
    elif args.all:
        files = sorted(conv_dir.glob("*.yaml"))
        if not files:
            print(f"ERROR: No conversation files found in {conv_dir}")
            sys.exit(1)
    else:
        print("ERROR: Specify --conversation <file> or --all")
        sys.exit(1)

    print(f"[Conversation Eval] Found {len(files)} conversation(s)")

    # Run evaluations
    results = []
    for conv_file in files:
        print(f"\n{'='*60}")
        print(f"Evaluating: {conv_file.name}")
        print('='*60)

        result = evaluator.evaluate_conversation(str(conv_file))
        results.append(result)

        # Print turn-by-turn
        for turn in result.turns:
            status = "PASS" if turn.passed else "FAIL"
            print(f"  Turn {turn.turn_number}: {status} ({turn.composite_score:.1f})")

            if args.debug:
                print(f"    Original: {turn.user_query}")
                if turn.reformulated_query and turn.reformulated_query != turn.user_query:
                    print(f"    Reformulated: {turn.reformulated_query}")
                print(f"    Accuracy: {turn.factual_accuracy:.0f}/5")
                print(f"    Completeness: {turn.completeness:.0f}/5")
                print(f"    Context: {turn.context_resolution:.2f}")
                print(f"    Coherence: {turn.coherence:.0f}/3")
                # Truncate response for display
                resp = turn.response[:150] + "..." if len(turn.response) > 150 else turn.response
                print(f"    Response: {resp}")

        # Conversation summary
        conv_status = "PASS" if result.conversation_passed else "FAIL"
        print(f"\n  Conversation: {conv_status}")
        print(f"  Average Score: {result.average_score:.1f}")
        print(f"  Context Resolution: {result.context_resolution_rate:.1%}")
        print(f"  All Turns Passed: {result.all_turns_passed}")

    # Overall summary
    print_summary(results)

    # Exit with appropriate code
    all_passed = all(r.conversation_passed for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
