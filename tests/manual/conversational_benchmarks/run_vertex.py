"""
Conversational Intelligence Test for Vertex AI Agent Handler
"""

import sys
import time
from pathlib import Path

# Add project root to path for chatbot imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from chatbot.handlers.vertex_agent_handler import VertexAgentHandler
from test_definitions import TESTS, save_results, write_report


def run_conversation(handler: VertexAgentHandler, test: dict, thread_id: str) -> dict:
    """Run a single test conversation using the handler."""
    print(f"\n{'='*60}")
    print(f"Running: {test['name']}")
    print(f"Thread ID: {thread_id}")
    print(f"{'='*60}")

    turns_results = []

    for i, user_query in enumerate(test["turns"], 1):
        print(f"\n[Turn {i}] User: {user_query}")
        start_time = time.time()

        # Use handler interface (same as OpenAI agent)
        result = handler.handle(user_query, thread_id=thread_id)

        elapsed = time.time() - start_time
        response = result.get("answer", "")
        sources = result.get("sources", [])

        print(f"[Turn {i}] Assistant: {response}")
        print(f"[Turn {i}] Time: {elapsed:.2f}s")

        turns_results.append({
            "turn": i,
            "user": user_query,
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
    print("CONVERSATIONAL INTELLIGENCE TEST - VERTEX AI AGENT HANDLER")
    print("=" * 60)

    print("\nInitializing Vertex AI Agent Handler...")
    handler = VertexAgentHandler()

    results = {
        "system": "vertex_agent_handler",
        "tests": []
    }

    for test in TESTS:
        thread_id = f"test_{test['id']}"
        test_result = run_conversation(handler, test, thread_id)
        results["tests"].append(test_result)

    json_path = save_results(results, "vertex")
    report_path = write_report(results, "vertex", "Vertex AI Agent Handler")

    print(f"\n{'='*60}")
    print(f"Results saved to: {json_path}")
    print(f"Report saved to: {report_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
