"""
Conversational Intelligence Test for Custom RAG Chatbot
"""

import os
import sys
import time
from pathlib import Path

# Force conversational mode
os.environ["CONVERSATIONAL_MODE"] = "true"

# Add parent directory to path for chatbot imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot.chatbot import TexasChildcareChatbot
from test_definitions import TESTS, save_results, write_report


def run_conversation(chatbot: TexasChildcareChatbot, test: dict, thread_id: str) -> dict:
    """Run a single test conversation and capture all turns."""
    print(f"\n{'='*60}")
    print(f"Running: {test['name']}")
    print(f"Thread ID: {thread_id}")
    print(f"{'='*60}")

    turns_results = []

    for i, user_query in enumerate(test["turns"], 1):
        print(f"\n[Turn {i}] User: {user_query}")

        start_time = time.time()

        result = chatbot.ask(user_query, thread_id=thread_id)

        elapsed = time.time() - start_time

        response = result.get("answer", "")
        reformulated = result.get("reformulated_query")
        sources = result.get("sources", [])

        print(f"[Turn {i}] Assistant: {response}")
        if reformulated and reformulated != user_query:
            print(f"[Turn {i}] Reformulated: {reformulated}")
        print(f"[Turn {i}] Time: {elapsed:.2f}s")

        turns_results.append({
            "turn": i,
            "user": user_query,
            "reformulated_query": reformulated,
            "assistant": response,
            "sources": sources,
            "elapsed_seconds": round(elapsed, 2)
        })

    return {
        "test_id": test["id"],
        "test_name": test["name"],
        "description": test["description"],
        "success_criteria": test["success_criteria"],
        "thread_id": thread_id,
        "turns": turns_results,
        "total_turns": len(turns_results)
    }


def main():
    print("=" * 60)
    print("CONVERSATIONAL INTELLIGENCE TEST - CUSTOM RAG")
    print("=" * 60)

    print("\nInitializing chatbot...")
    chatbot = TexasChildcareChatbot()

    results = {
        "system": "custom_rag",
        "conversational_mode": True,
        "tests": []
    }

    for test in TESTS:
        thread_id = f"test_{test['id']}"
        test_result = run_conversation(chatbot, test, thread_id)
        results["tests"].append(test_result)

    json_path = save_results(results, "conversational_test_rag")
    report_path = write_report(results, "conversational_test_rag", "Custom RAG (LangGraph + Qdrant)")

    print(f"\n{'='*60}")
    print(f"Results saved to: {json_path}")
    print(f"Report saved to: {report_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
